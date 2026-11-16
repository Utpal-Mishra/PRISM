from __future__ import annotations

import hashlib
import json
import re
import time
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.ai_providers import (
    AIProviderPolicyError,
    read_provider_secret,
    validate_provider_policy,
)
from enterprise.config import EnterpriseSettings, get_settings
from enterprise.models import AIProviderConfig, EvidenceRecord
from enterprise.phase18_models import AICallAudit, ModelEvaluation, ModelRegistryRecord
from enterprise.tenancy import WorkspaceAccess, clearance_allows

INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore\s+(all\s+)?previous",
        r"reveal\s+(the\s+)?system\s+prompt",
        r"developer\s+message",
        r"bypass\s+(the\s+)?policy",
        r"show\s+(me\s+)?secrets?",
        r"exfiltrat",
        r"disable\s+(the\s+)?guardrail",
    ]
]
REDACTION_PATTERNS = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),
]
CLASSIFICATION_RANK = {
    "public": 10,
    "internal": 20,
    "confidential": 30,
    "restricted": 40,
}


class AIGatewayError(RuntimeError):
    pass


def redact_text(value: str) -> tuple[str, int]:
    redacted = value
    count = 0
    for pattern in REDACTION_PATTERNS:
        redacted, replacements = pattern.subn("[REDACTED]", redacted)
        count += replacements
    return redacted, count


def prompt_injection_detected(value: str) -> bool:
    return any(pattern.search(value) for pattern in INJECTION_PATTERNS)


def _classification_allows(ceiling: str, classification: str) -> bool:
    return CLASSIFICATION_RANK.get(classification, 99) <= CLASSIFICATION_RANK.get(
        ceiling,
        -1,
    )


def _prompt_hash(system_text: str, user_text: str) -> str:
    return hashlib.sha256(
        f"{system_text}\n---\n{user_text}".encode("utf-8")
    ).hexdigest()


def _record_audit(
    db: Session,
    access: WorkspaceAccess,
    *,
    model: ModelRegistryRecord,
    decision_case_id: str | None,
    prompt_hash: str,
    classification: str,
    evidence_ids: list[str],
    redaction_count: int,
    injection_flag: bool,
    output_status: str,
    token_usage: dict | None = None,
    latency_ms: int | None = None,
    detail: dict | None = None,
) -> AICallAudit:
    record = AICallAudit(
        id=f"AIAUD-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        model_registry_id=model.id,
        decision_case_id=decision_case_id,
        prompt_hash=prompt_hash,
        classification=classification,
        evidence_ids=evidence_ids,
        redaction_count=redaction_count,
        injection_flag=injection_flag,
        output_status=output_status,
        token_usage=token_usage or {},
        latency_ms=latency_ms,
        detail=detail or {},
    )
    db.add(record)
    db.flush()
    return record


def invoke_model(
    db: Session,
    access: WorkspaceAccess,
    *,
    model_alias: str,
    question: str,
    classification: str,
    evidence_ids: list[str],
    decision_case_id: str | None = None,
    settings: EnterpriseSettings | None = None,
) -> dict:
    settings = settings or get_settings()
    model = db.scalar(
        select(ModelRegistryRecord).where(
            ModelRegistryRecord.tenant_id == access.tenant_id,
            ModelRegistryRecord.workspace_id == access.workspace_id,
            ModelRegistryRecord.alias == model_alias,
            ModelRegistryRecord.enabled.is_(True),
        )
    )
    if model is None:
        raise AIGatewayError("Enabled model registry record was not found.")
    if model.api_style != "openai_compatible":
        raise AIGatewayError(
            "Only openai_compatible API style is enabled in this release."
        )
    if not clearance_allows(access.data_clearance, classification):
        raise AIGatewayError(
            "Caller clearance is below the requested AI classification."
        )
    if not _classification_allows(model.classification_ceiling, classification):
        raise AIGatewayError("Model classification ceiling blocks this request.")

    evaluation = db.scalar(
        select(ModelEvaluation)
        .where(
            ModelEvaluation.tenant_id == access.tenant_id,
            ModelEvaluation.workspace_id == access.workspace_id,
            ModelEvaluation.model_registry_id == model.id,
            ModelEvaluation.passed.is_(True),
        )
        .order_by(ModelEvaluation.completed_at.desc())
        .limit(1)
    )
    if evaluation is None:
        raise AIGatewayError("Model has no passing governed evaluation.")

    provider = db.get(AIProviderConfig, model.provider_config_id)
    if (
        provider is None
        or provider.tenant_id != access.tenant_id
        or provider.workspace_id != access.workspace_id
        or not provider.enabled
    ):
        raise AIGatewayError("Approved AI provider configuration is unavailable.")
    try:
        validate_provider_policy(provider.endpoint_host, provider.data_policy, settings)
    except AIProviderPolicyError as exc:
        raise AIGatewayError(str(exc)) from exc

    allowed_classes = provider.data_policy.get("allowed_data_classes", [])
    if classification not in allowed_classes:
        raise AIGatewayError("Provider data policy blocks this classification.")

    unique_evidence = list(dict.fromkeys(evidence_ids))
    records = db.scalars(
        select(EvidenceRecord).where(
            EvidenceRecord.tenant_id == access.tenant_id,
            EvidenceRecord.workspace_id == access.workspace_id,
            EvidenceRecord.id.in_(unique_evidence),
        )
    ).all()
    found = {record.id: record for record in records}
    if set(found) != set(unique_evidence):
        raise AIGatewayError("AI request contains unknown evidence identifiers.")
    for record in records:
        if not _classification_allows(classification, record.classification):
            raise AIGatewayError(
                "Evidence classification exceeds the AI request boundary."
            )

    evidence_payload = [
        {
            "evidence_id": record.id,
            "evidence_class": record.evidence_class,
            "classification": record.classification,
            "payload": record.payload,
        }
        for record in records
    ]
    system_text = (
        "You are operating inside PRISM's governed evidence runtime. "
        "Use only the supplied evidence. Do not invent facts or causality. "
        "Return strict JSON with keys answer, evidence_ids, limitations, "
        "causal_status. evidence_ids must contain only supplied EVD identifiers."
    )
    user_text = json.dumps(
        {"question": question, "evidence": evidence_payload},
        sort_keys=True,
        default=str,
    )
    if len(user_text) > settings.ai_provider_max_input_chars:
        raise AIGatewayError("AI request exceeds the configured input limit.")

    injection_flag = prompt_injection_detected(question)
    prompt_hash = _prompt_hash(system_text, user_text)
    if injection_flag:
        _record_audit(
            db,
            access,
            model=model,
            decision_case_id=decision_case_id,
            prompt_hash=prompt_hash,
            classification=classification,
            evidence_ids=unique_evidence,
            redaction_count=0,
            injection_flag=True,
            output_status="blocked_prompt_injection",
            detail={"prompt_body_stored": False},
        )
        raise AIGatewayError("Prompt-injection policy blocked this request.")

    redacted_user, redactions = redact_text(user_text)
    secret = read_provider_secret(db, provider)
    api_key = str(secret.get("api_key", ""))
    if not api_key:
        raise AIGatewayError("AI provider credential is incomplete.")

    url = f"https://{provider.endpoint_host}{model.endpoint_path}"
    started = time.perf_counter()
    try:
        with httpx.Client(
            timeout=settings.ai_gateway_timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "model": model.model_name,
                    "messages": [
                        {"role": "system", "content": system_text},
                        {"role": "user", "content": redacted_user},
                    ],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            provider_body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_audit(
            db,
            access,
            model=model,
            decision_case_id=decision_case_id,
            prompt_hash=prompt_hash,
            classification=classification,
            evidence_ids=unique_evidence,
            redaction_count=redactions,
            injection_flag=False,
            output_status="provider_error",
            latency_ms=latency_ms,
            detail={"prompt_body_stored": False},
        )
        raise AIGatewayError("AI provider request failed.") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    try:
        output = provider_body["choices"][0]["message"]["content"]
        if len(output) > settings.ai_gateway_max_output_chars:
            raise AIGatewayError("AI output exceeds the configured output limit.")
        cleaned = str(output).strip()
        fence = chr(96) * 3
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence):].lstrip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].lstrip()
            if cleaned.endswith(fence):
                cleaned = cleaned[:-len(fence)].rstrip()
        result = json.loads(cleaned)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _record_audit(
            db,
            access,
            model=model,
            decision_case_id=decision_case_id,
            prompt_hash=prompt_hash,
            classification=classification,
            evidence_ids=unique_evidence,
            redaction_count=redactions,
            injection_flag=False,
            output_status="invalid_output",
            latency_ms=latency_ms,
            detail={"prompt_body_stored": False},
        )
        raise AIGatewayError(
            "AI provider returned an invalid governed response."
        ) from exc

    cited = result.get("evidence_ids")
    if not isinstance(cited, list) or any(
        item not in unique_evidence for item in cited
    ):
        status_value = "invalid_citations"
    elif unique_evidence and not cited:
        status_value = "missing_citations"
    elif result.get("causal_status") not in {
        "causal-not-established",
        "causal-established-with-approved-method",
    }:
        status_value = "invalid_causal_status"
    else:
        status_value = "accepted"

    usage = provider_body.get("usage", {})
    audit = _record_audit(
        db,
        access,
        model=model,
        decision_case_id=decision_case_id,
        prompt_hash=prompt_hash,
        classification=classification,
        evidence_ids=unique_evidence,
        redaction_count=redactions,
        injection_flag=False,
        output_status=status_value,
        token_usage=usage if isinstance(usage, dict) else {},
        latency_ms=latency_ms,
        detail={
            "prompt_body_stored": False,
            "provider": provider.provider,
            "model": model.model_name,
            "prompt_version": model.prompt_version,
            "transparency_notice": model.transparency_notice,
        },
    )
    if status_value != "accepted":
        raise AIGatewayError(
            f"AI output failed governance validation: {status_value}."
        )

    return {
        "ai_audit_id": audit.id,
        "model_alias": model.alias,
        "answer": result.get("answer", ""),
        "evidence_ids": cited,
        "limitations": result.get("limitations", []),
        "causal_status": result.get("causal_status"),
        "transparency_notice": model.transparency_notice,
        "human_review_required": True,
        "latency_ms": latency_ms,
        "token_usage": audit.token_usage,
    }

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.ai_runtime import AIGatewayError, invoke_model
from enterprise.audit import append_audit_event
from enterprise.config import get_settings
from enterprise.db import SessionLocal, get_db
from enterprise.models import AIProviderConfig
from enterprise.p2_models import DecisionCase
from enterprise.phase18_models import AICallAudit, ModelEvaluation, ModelRegistryRecord
from enterprise.quota import UsageLimitExceeded, enforce
from enterprise.tenancy import WorkspaceAccess, clearance_allows, require_role

router = APIRouter()
settings = get_settings()
DbDep = Annotated[Session, Depends(get_db)]
ViewerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("viewer"))]
AnalystAccessDep = Annotated[WorkspaceAccess, Depends(require_role("analyst"))]
AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role("admin"))]

Classification = Literal["public", "internal", "confidential", "restricted"]


class ModelRegistryInput(BaseModel):
    provider_config_id: str = Field(min_length=1, max_length=36)
    alias: str = Field(min_length=1, max_length=128)
    model_name: str = Field(min_length=1, max_length=128)
    api_style: Literal["openai_compatible"] = "openai_compatible"
    endpoint_path: str = Field(min_length=1, max_length=255)
    risk_classification: str = Field(min_length=1, max_length=64)
    intended_use: str = Field(min_length=8, max_length=4000)
    human_oversight: str = Field(min_length=8, max_length=4000)
    transparency_notice: str = Field(min_length=8, max_length=4000)
    classification_ceiling: Classification
    prompt_version: str = Field(default="v1", max_length=64)


class ModelEvaluationInput(BaseModel):
    evaluation_name: str = Field(min_length=1, max_length=200)
    dataset_version: str = Field(min_length=1, max_length=100)
    metrics: dict[str, float]
    thresholds: dict[str, float]
    reviewer: str = Field(min_length=1, max_length=255)


class GatewayInvokeInput(BaseModel):
    model_alias: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=4, max_length=8000)
    classification: Classification = "internal"
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)


class DecisionCaseAISynthesisInput(BaseModel):
    model_alias: str = Field(min_length=1, max_length=128)


def _consume_ai_quota(access: WorkspaceAccess) -> None:
    with SessionLocal.begin() as control_db:
        try:
            enforce(
                control_db,
                access,
                action="ai_gateway_calls",
                limit=settings.ai_gateway_daily_call_quota,
                window_seconds=86400,
            )
        except UsageLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "ai_gateway_daily_quota_exceeded",
                    "limit": exc.decision.limit,
                    "retry_after_seconds": exc.decision.retry_after_seconds,
                },
                headers={"Retry-After": str(exc.decision.retry_after_seconds)},
            ) from exc


@router.get("/v1/workspaces/{workspace_id}/ai/models")
def list_models(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(ModelRegistryRecord)
        .where(
            ModelRegistryRecord.tenant_id == access.tenant_id,
            ModelRegistryRecord.workspace_id == access.workspace_id,
        )
        .order_by(ModelRegistryRecord.alias.asc())
    ).all()
    return [
        {
            "model_registry_id": row.id,
            "provider_config_id": row.provider_config_id,
            "alias": row.alias,
            "model_name": row.model_name,
            "api_style": row.api_style,
            "risk_classification": row.risk_classification,
            "intended_use": row.intended_use,
            "human_oversight": row.human_oversight,
            "transparency_notice": row.transparency_notice,
            "classification_ceiling": row.classification_ceiling,
            "enabled": row.enabled,
            "prompt_version": row.prompt_version,
        }
        for row in rows
        if clearance_allows(access.data_clearance, row.classification_ceiling)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/ai/models",
    status_code=status.HTTP_201_CREATED,
)
def register_model(
    body: ModelRegistryInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str | bool]:
    if not body.endpoint_path.startswith("/") or "://" in body.endpoint_path:
        raise HTTPException(
            status_code=400,
            detail="Model endpoint_path must be relative to the approved provider host.",
        )
    if not clearance_allows(access.data_clearance, body.classification_ceiling):
        raise HTTPException(
            status_code=403,
            detail="Admin clearance is below the model classification ceiling.",
        )
    provider = db.scalar(
        select(AIProviderConfig).where(
            AIProviderConfig.id == body.provider_config_id,
            AIProviderConfig.tenant_id == access.tenant_id,
            AIProviderConfig.workspace_id == access.workspace_id,
        )
    )
    if provider is None:
        raise HTTPException(status_code=404, detail="AI provider configuration was not found.")

    record = ModelRegistryRecord(
        id=f"MODEL-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
        enabled=False,
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="model_registered",
        object_type="model_registry",
        object_id=record.id,
        detail={
            "alias": record.alias,
            "risk_classification": record.risk_classification,
            "classification_ceiling": record.classification_ceiling,
        },
    )
    db.commit()
    return {"model_registry_id": record.id, "enabled": record.enabled}


@router.post(
    "/v1/workspaces/{workspace_id}/ai/models/{model_id}/evaluations",
    status_code=status.HTTP_201_CREATED,
)
def record_evaluation(
    model_id: str,
    body: ModelEvaluationInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    model = db.scalar(
        select(ModelRegistryRecord).where(
            ModelRegistryRecord.id == model_id,
            ModelRegistryRecord.tenant_id == access.tenant_id,
            ModelRegistryRecord.workspace_id == access.workspace_id,
        )
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Model registry record was not found.")
    missing = [key for key in body.thresholds if key not in body.metrics]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={"code": "missing_evaluation_metrics", "metrics": missing},
        )
    passed = all(
        body.metrics[key] >= threshold
        for key, threshold in body.thresholds.items()
    )
    record = ModelEvaluation(
        id=f"EVAL-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        model_registry_id=model.id,
        evaluation_name=body.evaluation_name,
        dataset_version=body.dataset_version,
        metrics=body.metrics,
        thresholds=body.thresholds,
        passed=passed,
        reviewer=body.reviewer,
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="model_evaluation_recorded",
        object_type="model_evaluation",
        object_id=record.id,
        detail={"model_registry_id": model.id, "passed": passed},
    )
    db.commit()
    return {"evaluation_id": record.id, "passed": passed}


@router.post("/v1/workspaces/{workspace_id}/ai/models/{model_id}/enable")
def enable_model(
    model_id: str,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    model = db.scalar(
        select(ModelRegistryRecord)
        .where(
            ModelRegistryRecord.id == model_id,
            ModelRegistryRecord.tenant_id == access.tenant_id,
            ModelRegistryRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Model registry record was not found.")
    passing = db.scalar(
        select(ModelEvaluation).where(
            ModelEvaluation.tenant_id == access.tenant_id,
            ModelEvaluation.workspace_id == access.workspace_id,
            ModelEvaluation.model_registry_id == model.id,
            ModelEvaluation.passed.is_(True),
        )
    )
    if passing is None:
        raise HTTPException(
            status_code=409,
            detail="Model requires at least one passing evaluation before enablement.",
        )
    provider = db.get(AIProviderConfig, model.provider_config_id)
    if provider is None or not provider.enabled:
        raise HTTPException(
            status_code=409,
            detail="Model provider must be enabled before the model can be enabled.",
        )
    model.enabled = True
    append_audit_event(
        db,
        access,
        event_type="model_enabled",
        object_type="model_registry",
        object_id=model.id,
        detail={"alias": model.alias, "prompt_version": model.prompt_version},
    )
    db.commit()
    return {"model_registry_id": model.id, "enabled": model.enabled}


@router.post("/v1/workspaces/{workspace_id}/ai/gateway/invoke")
def invoke_gateway(
    body: GatewayInvokeInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _consume_ai_quota(access)
    try:
        result = invoke_model(
            db,
            access,
            model_alias=body.model_alias,
            question=body.question,
            classification=body.classification,
            evidence_ids=body.evidence_ids,
        )
    except AIGatewayError as exc:
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return result


@router.post(
    "/v1/workspaces/{workspace_id}/decision-cases/{case_id}/ai-synthesis"
)
def synthesize_decision_case(
    case_id: str,
    body: DecisionCaseAISynthesisInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _consume_ai_quota(access)
    case = db.scalar(
        select(DecisionCase)
        .where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == access.tenant_id,
            DecisionCase.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Decision Case was not found.")
    if not clearance_allows(access.data_clearance, case.classification):
        raise HTTPException(status_code=403, detail="Decision Case clearance is required.")
    if case.status != "completed" or not case.evidence_ids:
        raise HTTPException(
            status_code=409,
            detail="Decision Case must be completed with evidence before AI synthesis.",
        )
    try:
        result = invoke_model(
            db,
            access,
            model_alias=body.model_alias,
            question=case.business_question,
            classification=case.classification,
            evidence_ids=case.evidence_ids,
            decision_case_id=case.id,
        )
    except AIGatewayError as exc:
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    synthesis = dict(case.synthesis)
    synthesis["governed_ai_assist"] = {
        "ai_audit_id": result["ai_audit_id"],
        "model_alias": result["model_alias"],
        "answer": result["answer"],
        "evidence_ids": result["evidence_ids"],
        "limitations": result["limitations"],
        "causal_status": result["causal_status"],
        "transparency_notice": result["transparency_notice"],
    }
    case.synthesis = synthesis
    case.approval_state = "pending_human_review"
    case.reviewed_by = None
    case.reviewed_at = None
    case.review_rationale = None
    append_audit_event(
        db,
        access,
        event_type="decision_case_ai_synthesis_added",
        object_type="decision_case",
        object_id=case.id,
        detail={
            "ai_audit_id": result["ai_audit_id"],
            "model_alias": result["model_alias"],
            "human_review_required": True,
        },
    )
    db.commit()
    return {
        "decision_case_id": case.id,
        "approval_state": case.approval_state,
        "ai_result": result,
    }


@router.get("/v1/workspaces/{workspace_id}/ai/audit")
def list_ai_audit(
    access: AdminAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(AICallAudit)
        .where(
            AICallAudit.tenant_id == access.tenant_id,
            AICallAudit.workspace_id == access.workspace_id,
        )
        .order_by(AICallAudit.created_at.desc())
        .limit(500)
    ).all()
    return [
        {
            "ai_audit_id": row.id,
            "model_registry_id": row.model_registry_id,
            "decision_case_id": row.decision_case_id,
            "prompt_hash": row.prompt_hash,
            "classification": row.classification,
            "evidence_ids": row.evidence_ids,
            "redaction_count": row.redaction_count,
            "injection_flag": row.injection_flag,
            "output_status": row.output_status,
            "token_usage": row.token_usage,
            "latency_ms": row.latency_ms,
            "detail": row.detail,
            "created_at": row.created_at,
        }
        for row in rows
    ]

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.materialization import add_evidence_edge
from enterprise.models import EvidenceRecord
from enterprise.p2_models import AITeamRun, DecisionCase, EvidenceEdge

TEAM_REGISTRY = {
    "data": {
        "name": "Data Team",
        "responsibility": "Data readiness, quality, schema, provenance and materialisation.",
    },
    "analytics": {
        "name": "Analytics Team",
        "responsibility": "KPI, segmentation, statistical investigation and explanation.",
    },
    "data_science": {
        "name": "Data Science Team",
        "responsibility": "Forecasting, prediction, anomaly, simulation and optimisation evidence.",
    },
    "strategy": {
        "name": "Strategy Team",
        "responsibility": "Alternatives and evidence-grounded decision-support synthesis.",
    },
    "governance": {
        "name": "Governance Team",
        "responsibility": "Evidence, classification, lineage, limitations and review readiness.",
    },
}

TEAM_KEYWORDS = {
    "data": {
        "data",
        "dataset",
        "quality",
        "schema",
        "source",
        "connector",
        "field",
        "lineage",
        "missing",
    },
    "analytics": {
        "why",
        "kpi",
        "metric",
        "performance",
        "margin",
        "revenue",
        "cost",
        "segment",
        "relationship",
        "driver",
        "trend",
        "change",
    },
    "data_science": {
        "forecast",
        "predict",
        "prediction",
        "model",
        "scenario",
        "simulate",
        "simulation",
        "optimise",
        "optimize",
        "anomaly",
    },
    "strategy": {
        "should",
        "strategy",
        "recommend",
        "decision",
        "option",
        "action",
        "prioritise",
        "prioritize",
        "launch",
        "invest",
    },
}

CLASSIFICATION_RANK = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}

TEAM_EVIDENCE_HINTS = {
    "data": {"data", "quality", "schema", "connector", "registry", "lineage"},
    "analytics": {
        "descriptive",
        "association",
        "statistical",
        "investigation",
        "driver",
        "segment",
        "relationship",
        "outlier",
    },
    "data_science": {
        "forecast",
        "prediction",
        "predictive",
        "model",
        "scenario",
        "anomaly",
        "simulation",
    },
    "strategy": {
        "strategy",
        "decision",
        "outcome",
        "scenario",
        "driver",
        "forecast",
        "association",
    },
}


def team_registry() -> list[dict[str, str]]:
    return [
        {
            "team": key,
            "name": value["name"],
            "responsibility": value["responsibility"],
            "execution_mode": "deterministic_evidence_routing_v1",
        }
        for key, value in TEAM_REGISTRY.items()
    ]


def route_teams(question: str) -> list[str]:
    tokens = set(re.findall(r"[a-z0-9_]+", question.lower()))
    selected = [
        team
        for team, keywords in TEAM_KEYWORDS.items()
        if tokens.intersection(keywords)
    ]
    if not selected:
        selected = ["analytics"]
    if "governance" not in selected:
        selected.append("governance")
    return selected


def _classification_allowed(max_classification: str, classification: str) -> bool:
    return CLASSIFICATION_RANK.get(classification, 99) <= CLASSIFICATION_RANK.get(
        max_classification,
        -1,
    )


def _evidence_text(record: EvidenceRecord) -> str:
    return " ".join(
        [
            record.evidence_class,
            json.dumps(record.payload, default=str, sort_keys=True)[:8000],
        ]
    ).lower()


def _relevance_score(question: str, record: EvidenceRecord) -> int:
    question_tokens = set(re.findall(r"[a-z0-9_]+", question.lower()))
    question_tokens -= {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "for",
        "in",
        "on",
        "is",
        "are",
        "what",
        "we",
        "our",
    }
    evidence_text = _evidence_text(record)
    return sum(1 for token in question_tokens if token in evidence_text)


def select_evidence(
    db: Session,
    case: DecisionCase,
    settings: EnterpriseSettings | None = None,
) -> list[EvidenceRecord]:
    settings = settings or get_settings()
    statement = (
        select(EvidenceRecord)
        .where(
            EvidenceRecord.tenant_id == case.tenant_id,
            EvidenceRecord.workspace_id == case.workspace_id,
        )
        .order_by(EvidenceRecord.created_at.desc())
        .limit(500)
    )
    if case.requested_evidence_ids:
        statement = statement.where(
            EvidenceRecord.id.in_(case.requested_evidence_ids)
        )

    candidates = [
        record
        for record in db.scalars(statement).all()
        if _classification_allowed(case.max_classification, record.classification)
    ]
    ranked = sorted(
        candidates,
        key=lambda record: (
            _relevance_score(case.business_question, record),
            record.created_at,
        ),
        reverse=True,
    )
    if case.requested_evidence_ids:
        return ranked[: settings.decision_case_max_evidence]
    return [
        record
        for record in ranked
        if _relevance_score(case.business_question, record) > 0
    ][: settings.decision_case_max_evidence]


def _evidence_for_team(team: str, evidence: list[EvidenceRecord]) -> list[EvidenceRecord]:
    hints = TEAM_EVIDENCE_HINTS.get(team)
    if not hints:
        return evidence[:10]
    matched = [
        record
        for record in evidence
        if any(hint in record.evidence_class.lower() for hint in hints)
        or any(hint in _evidence_text(record) for hint in hints)
    ]
    return (matched or evidence)[:10]


def _extract(record: EvidenceRecord) -> dict:
    payload = record.payload
    extract: dict[str, object] = {
        "evidence_id": record.id,
        "evidence_class": record.evidence_class,
        "classification": record.classification,
    }
    for key in [
        "finding",
        "summary",
        "metric",
        "method",
        "row_count",
        "content_hash",
        "schema_summary",
        "causal_status",
    ]:
        if key in payload:
            extract[key] = payload[key]
    return extract


def _create_team_run(
    db: Session,
    case: DecisionCase,
    team: str,
    evidence: list[EvidenceRecord],
) -> AITeamRun:
    selected = _evidence_for_team(team, evidence)
    evidence_ids = [record.id for record in selected]
    finding: dict[str, object] = {
        "team_name": TEAM_REGISTRY[team]["name"],
        "summary": (
            f"{TEAM_REGISTRY[team]['name']} reviewed "
            f"{len(selected)} traceable PRISM evidence record(s)."
        ),
        "evidence_extracts": [_extract(record) for record in selected[:5]],
        "claim_boundary": (
            "This team run does not create independent facts; it organises "
            "and interprets the cited PRISM evidence."
        ),
        "causal_status": "causal-not-established",
    }
    if team == "strategy":
        finding["recommendation_state"] = "options_require_human_review"

    run = AITeamRun(
        tenant_id=case.tenant_id,
        workspace_id=case.workspace_id,
        created_by=case.created_by,
        decision_case_id=case.id,
        team=team,
        status="completed",
        evidence_ids=evidence_ids,
        finding=finding,
        method="deterministic_evidence_routing_v1",
        limitations=[
            "No live AI provider was invoked.",
            "Evidence relevance is deterministic and lexical, not semantic proof.",
            "Predictive or associative evidence does not establish causation.",
        ],
        completed_at=datetime.now(UTC),
    )
    db.add(run)
    db.flush()

    for record in selected:
        add_evidence_edge(
            db,
            tenant_id=case.tenant_id,
            workspace_id=case.workspace_id,
            created_by=case.created_by,
            source_type="evidence",
            source_id=record.id,
            target_type="ai_team_run",
            target_id=run.id,
            relation="supports",
            classification=record.classification,
            metadata_json={"team": team},
        )
    add_evidence_edge(
        db,
        tenant_id=case.tenant_id,
        workspace_id=case.workspace_id,
        created_by=case.created_by,
        source_type="ai_team_run",
        source_id=run.id,
        target_type="decision_case",
        target_id=case.id,
        relation="contributes_to",
        classification=case.max_classification,
        metadata_json={"team": team},
    )
    return run


def run_control_plane(
    db: Session,
    case: DecisionCase,
    settings: EnterpriseSettings | None = None,
) -> dict:
    settings = settings or get_settings()
    old_run_ids = db.scalars(
        select(AITeamRun.id).where(
            AITeamRun.tenant_id == case.tenant_id,
            AITeamRun.workspace_id == case.workspace_id,
            AITeamRun.decision_case_id == case.id,
        )
    ).all()
    if old_run_ids:
        db.execute(
            delete(EvidenceEdge).where(
                EvidenceEdge.tenant_id == case.tenant_id,
                EvidenceEdge.workspace_id == case.workspace_id,
                or_(
                    EvidenceEdge.source_id.in_(old_run_ids),
                    EvidenceEdge.target_id.in_(old_run_ids),
                ),
            )
        )
    db.execute(
        delete(AITeamRun).where(
            AITeamRun.tenant_id == case.tenant_id,
            AITeamRun.workspace_id == case.workspace_id,
            AITeamRun.decision_case_id == case.id,
        )
    )

    evidence = select_evidence(db, case, settings)
    if not evidence:
        governance = AITeamRun(
            tenant_id=case.tenant_id,
            workspace_id=case.workspace_id,
            created_by=case.created_by,
            decision_case_id=case.id,
            team="governance",
            status="insufficient_evidence",
            evidence_ids=[],
            finding={
                "team_name": "Governance Team",
                "summary": "PRISM cannot support this Decision Case with traceable evidence.",
                "review_ready": False,
                "required_action": (
                    "Add or generate relevant governed EVD-* evidence, then rerun the case."
                ),
            },
            method="deterministic_evidence_routing_v1",
            limitations=["No evidence-grounded analytical conclusion was produced."],
            completed_at=datetime.now(UTC),
        )
        db.add(governance)
        db.flush()
        case.status = "insufficient_evidence"
        case.participating_teams = ["governance"]
        case.evidence_ids = []
        case.approval_state = "not_reviewable"
        case.synthesis = {
            "status": "insufficient_evidence",
            "business_question": case.business_question,
            "evidence_ids": [],
            "causal_status": "causal-not-established",
            "method": "deterministic_control_plane_v1",
            "human_review_required": False,
        }
        return case.synthesis

    teams = route_teams(case.business_question)
    non_governance = [team for team in teams if team != "governance"]
    runs = [_create_team_run(db, case, team, evidence) for team in non_governance]
    grounded = all(run.evidence_ids for run in runs)

    governance = AITeamRun(
        tenant_id=case.tenant_id,
        workspace_id=case.workspace_id,
        created_by=case.created_by,
        decision_case_id=case.id,
        team="governance",
        status="completed" if grounded else "blocked",
        evidence_ids=sorted({item for run in runs for item in run.evidence_ids}),
        finding={
            "team_name": "Governance Team",
            "summary": (
                "Governance verified that each specialist team cites traceable "
                "PRISM evidence."
                if grounded
                else "Governance blocked review because one or more team runs lack evidence."
            ),
            "review_ready": grounded,
            "causal_status": "causal-not-established",
            "human_approval_required": (
                case.materiality == "material" or "strategy" in non_governance
            ),
        },
        method="evidence_and_policy_review_v1",
        limitations=[
            "Governance review validates traceability, not business correctness.",
            "Material recommendations still require an accountable human decision.",
        ],
        completed_at=datetime.now(UTC),
    )
    db.add(governance)
    db.flush()
    add_evidence_edge(
        db,
        tenant_id=case.tenant_id,
        workspace_id=case.workspace_id,
        created_by=case.created_by,
        source_type="ai_team_run",
        source_id=governance.id,
        target_type="decision_case",
        target_id=case.id,
        relation="governs",
        classification=case.max_classification,
    )

    case.participating_teams = teams
    case.evidence_ids = sorted({record.id for record in evidence})
    case.status = "completed" if grounded else "blocked"
    human_review = case.materiality == "material" or "strategy" in non_governance
    case.approval_state = "pending_human_review" if grounded and human_review else (
        "analysis_only" if grounded else "not_reviewable"
    )
    case.synthesis = {
        "status": "evidence_grounded" if grounded else "blocked",
        "business_question": case.business_question,
        "participating_teams": teams,
        "evidence_ids": case.evidence_ids,
        "team_run_ids": [run.id for run in runs] + [governance.id],
        "method": "deterministic_control_plane_v1",
        "causal_status": "causal-not-established",
        "human_review_required": human_review,
        "execution_boundary": (
            "No operational action is executed by the Control Plane. "
            "Approved decisions remain separate governed records."
        ),
    }
    return case.synthesis

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event
from enterprise.config import get_settings
from enterprise.control_plane import team_registry
from enterprise.db import SessionLocal, get_db
from enterprise.jobs import enqueue_job
from enterprise.materialization import add_evidence_edge
from enterprise.models import Connector, ConnectorRun, DecisionRecord, EvidenceRecord
from enterprise.p2_models import (
    AITeamRun,
    DataAsset,
    DataSnapshot,
    DecisionCase,
    EvidenceEdge,
)
from enterprise.quota import UsageLimitExceeded, enforce
from enterprise.tenancy import WorkspaceAccess, clearance_allows, require_role

settings = get_settings()
router = APIRouter()


class DataAssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    owner: str = Field(min_length=1, max_length=255)
    classification: Literal["public", "internal", "confidential", "restricted"] = "internal"
    connector_id: str = Field(min_length=1, max_length=36)


class DataMaterializeInput(BaseModel):
    operation: dict[str, Any]


class DecisionCaseCreate(BaseModel):
    business_question: str = Field(min_length=8, max_length=4000)
    owner: str = Field(min_length=1, max_length=255)
    materiality: Literal["advisory", "material"] = "advisory"
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)


class DecisionCaseReview(BaseModel):
    action: Literal["approve", "reject"]
    rationale: str = Field(min_length=8, max_length=1000)


class DecisionPromotionInput(BaseModel):
    selected_action: str = Field(min_length=8, max_length=4000)
    expected_outcome: str = Field(min_length=8, max_length=4000)
    alternative_considered: str = Field(default="", max_length=4000)
    review_date: date


DbDep = Annotated[Session, Depends(get_db)]
ViewerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("viewer"))]
AnalystAccessDep = Annotated[WorkspaceAccess, Depends(require_role("analyst"))]
ManagerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("manager"))]


def _consume_limit(
    access: WorkspaceAccess,
    *,
    action: str,
    limit: int,
    window_seconds: int,
) -> None:
    with SessionLocal.begin() as control_db:
        try:
            enforce(
                control_db,
                access,
                action=action,
                limit=limit,
                window_seconds=window_seconds,
            )
        except UsageLimitExceeded as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "workspace_usage_limit_exceeded",
                    "action": action,
                    "limit": exc.decision.limit,
                    "retry_after_seconds": exc.decision.retry_after_seconds,
                },
                headers={"Retry-After": str(exc.decision.retry_after_seconds)},
            ) from exc


def _limit_write(access: WorkspaceAccess) -> None:
    _consume_limit(
        access,
        action="api_write",
        limit=settings.rate_limit_per_minute,
        window_seconds=60,
    )


def _limit_job(access: WorkspaceAccess) -> None:
    _consume_limit(
        access,
        action="jobs",
        limit=settings.workspace_daily_job_quota,
        window_seconds=86400,
    )


def _case_payload(case: DecisionCase) -> dict[str, Any]:
    return {
        "decision_case_id": case.id,
        "business_question": case.business_question,
        "owner": case.owner,
        "materiality": case.materiality,
        "status": case.status,
        "approval_state": case.approval_state,
        "participating_teams": case.participating_teams,
        "requested_evidence_ids": case.requested_evidence_ids,
        "evidence_ids": case.evidence_ids,
        "synthesis": case.synthesis,
        "job_id": case.job_id,
        "approved_by": case.approved_by,
        "approved_at": case.approved_at,
        "review_rationale": case.review_rationale,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


@router.get("/v1/workspaces/{workspace_id}/ai-teams")
def list_ai_teams(access: ViewerAccessDep) -> dict[str, Any]:
    return {
        "mode": "deterministic_evidence_routing_v1",
        "provider_invocation": False,
        "teams": team_registry(),
        "guardrail": "No team may present an unsupported claim as PRISM evidence.",
    }


@router.get("/v1/workspaces/{workspace_id}/data-assets")
def list_data_assets(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    assets = db.scalars(
        select(DataAsset)
        .where(
            DataAsset.tenant_id == access.tenant_id,
            DataAsset.workspace_id == access.workspace_id,
            DataAsset.status == "active",
        )
        .order_by(DataAsset.created_at.desc())
        .limit(200)
    ).all()
    return [
        {
            "data_asset_id": asset.id,
            "name": asset.name,
            "description": asset.description,
            "owner": asset.owner,
            "classification": asset.classification,
            "source_connector_id": asset.source_connector_id,
            "latest_snapshot_id": asset.latest_snapshot_id,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at,
        }
        for asset in assets
        if clearance_allows(access.data_clearance, asset.classification)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/data-assets",
    status_code=status.HTTP_201_CREATED,
)
def create_data_asset(
    body: DataAssetCreate,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    if not clearance_allows(access.data_clearance, body.classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership data clearance does not allow this classification.",
        )

    connector = db.scalar(
        select(Connector).where(
            Connector.id == body.connector_id,
            Connector.tenant_id == access.tenant_id,
            Connector.workspace_id == access.workspace_id,
            Connector.status == "active",
        )
    )
    if connector is None:
        raise HTTPException(status_code=404, detail="Active connector was not found.")

    duplicate = db.scalar(
        select(DataAsset).where(
            DataAsset.tenant_id == access.tenant_id,
            DataAsset.workspace_id == access.workspace_id,
            DataAsset.name == body.name,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A data asset with this name already exists in the workspace.",
        )

    asset = DataAsset(
        id=f"DATA-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name=body.name,
        description=body.description,
        owner=body.owner,
        classification=body.classification,
        source_connector_id=connector.id,
        status="active",
    )
    db.add(asset)
    db.flush()
    add_evidence_edge(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        source_type="connector",
        source_id=connector.id,
        target_type="data_asset",
        target_id=asset.id,
        relation="registered_source",
        classification=asset.classification,
    )
    append_audit_event(
        db,
        access,
        event_type="data_asset_created",
        object_type="data_asset",
        object_id=asset.id,
        detail={
            "name": asset.name,
            "classification": asset.classification,
            "source_connector_id": connector.id,
        },
    )
    db.commit()
    return {"data_asset_id": asset.id}


@router.post(
    "/v1/workspaces/{workspace_id}/data-assets/{asset_id}/materialize",
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_data_materialization(
    asset_id: str,
    body: DataMaterializeInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    _limit_job(access)
    asset = db.scalar(
        select(DataAsset).where(
            DataAsset.id == asset_id,
            DataAsset.tenant_id == access.tenant_id,
            DataAsset.workspace_id == access.workspace_id,
            DataAsset.status == "active",
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Data asset was not found.")
    if not clearance_allows(access.data_clearance, asset.classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership data clearance does not allow this data asset.",
        )

    connector = db.scalar(
        select(Connector).where(
            Connector.id == asset.source_connector_id,
            Connector.tenant_id == access.tenant_id,
            Connector.workspace_id == access.workspace_id,
            Connector.status == "active",
        )
    )
    if connector is None:
        raise HTTPException(status_code=404, detail="Source connector was not found.")

    run = ConnectorRun(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        connector_id=connector.id,
        status="queued",
    )
    db.add(run)
    db.flush()
    job = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="dataset_materialize",
        payload={
            "asset_id": asset.id,
            "connector_id": connector.id,
            "run_id": run.id,
            "operation": body.operation,
        },
        settings=settings,
    )
    run.job_id = job.id
    append_audit_event(
        db,
        access,
        event_type="data_materialization_queued",
        object_type="data_asset",
        object_id=asset.id,
        detail={
            "connector_id": connector.id,
            "connector_run_id": run.id,
            "job_id": job.id,
        },
    )
    db.commit()
    return {"data_asset_id": asset.id, "run_id": run.id, "job_id": job.id}


@router.get("/v1/workspaces/{workspace_id}/data-assets/{asset_id}/snapshots")
def list_data_snapshots(
    asset_id: str,
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    asset = db.scalar(
        select(DataAsset).where(
            DataAsset.id == asset_id,
            DataAsset.tenant_id == access.tenant_id,
            DataAsset.workspace_id == access.workspace_id,
        )
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Data asset was not found.")
    if not clearance_allows(access.data_clearance, asset.classification):
        raise HTTPException(status_code=403, detail="Data asset clearance is required.")

    snapshots = db.scalars(
        select(DataSnapshot)
        .where(
            DataSnapshot.tenant_id == access.tenant_id,
            DataSnapshot.workspace_id == access.workspace_id,
            DataSnapshot.asset_id == asset.id,
        )
        .order_by(DataSnapshot.version.desc())
        .limit(100)
    ).all()
    return [
        {
            "snapshot_id": item.id,
            "version": item.version,
            "classification": item.classification,
            "row_count": item.row_count,
            "size_bytes": item.size_bytes,
            "content_hash": item.content_hash,
            "schema_summary": item.schema_summary,
            "provenance": item.provenance,
            "immutable": item.immutable,
            "created_at": item.created_at,
        }
        for item in snapshots
    ]


@router.get(
    "/v1/workspaces/{workspace_id}/data-assets/{asset_id}/snapshots/{snapshot_id}"
)
def get_data_snapshot(
    asset_id: str,
    snapshot_id: str,
    access: ViewerAccessDep,
    db: DbDep,
    include_rows: bool = False,
) -> dict[str, Any]:
    snapshot = db.scalar(
        select(DataSnapshot).where(
            DataSnapshot.id == snapshot_id,
            DataSnapshot.asset_id == asset_id,
            DataSnapshot.tenant_id == access.tenant_id,
            DataSnapshot.workspace_id == access.workspace_id,
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Data snapshot was not found.")
    if not clearance_allows(access.data_clearance, snapshot.classification):
        raise HTTPException(status_code=403, detail="Data snapshot clearance is required.")

    result: dict[str, Any] = {
        "snapshot_id": snapshot.id,
        "asset_id": snapshot.asset_id,
        "version": snapshot.version,
        "classification": snapshot.classification,
        "row_count": snapshot.row_count,
        "size_bytes": snapshot.size_bytes,
        "content_hash": snapshot.content_hash,
        "schema_summary": snapshot.schema_summary,
        "provenance": snapshot.provenance,
        "immutable": snapshot.immutable,
        "created_at": snapshot.created_at,
    }
    if include_rows:
        result["rows"] = snapshot.rows
    return result


@router.get("/v1/workspaces/{workspace_id}/evidence-graph")
def get_evidence_graph(
    access: ViewerAccessDep,
    db: DbDep,
    node_id: str | None = None,
) -> dict[str, Any]:
    statement = (
        select(EvidenceEdge)
        .where(
            EvidenceEdge.tenant_id == access.tenant_id,
            EvidenceEdge.workspace_id == access.workspace_id,
        )
        .order_by(EvidenceEdge.created_at.desc())
        .limit(500)
    )
    if node_id:
        statement = statement.where(
            or_(
                EvidenceEdge.source_id == node_id,
                EvidenceEdge.target_id == node_id,
            )
        )
    edges = [
        edge
        for edge in db.scalars(statement).all()
        if clearance_allows(access.data_clearance, edge.classification)
    ]
    return {
        "node_id": node_id,
        "edge_count": len(edges),
        "edges": [
            {
                "edge_id": edge.id,
                "source_type": edge.source_type,
                "source_id": edge.source_id,
                "target_type": edge.target_type,
                "target_id": edge.target_id,
                "relation": edge.relation,
                "classification": edge.classification,
                "metadata": edge.metadata_json,
                "created_at": edge.created_at,
            }
            for edge in edges
        ],
    }


@router.get("/v1/workspaces/{workspace_id}/decision-cases")
def list_decision_cases(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    cases = db.scalars(
        select(DecisionCase)
        .where(
            DecisionCase.tenant_id == access.tenant_id,
            DecisionCase.workspace_id == access.workspace_id,
        )
        .order_by(DecisionCase.created_at.desc())
        .limit(200)
    ).all()
    return [
        _case_payload(case)
        for case in cases
        if clearance_allows(access.data_clearance, case.max_classification)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/decision-cases",
    status_code=status.HTTP_202_ACCEPTED,
)
def create_decision_case(
    body: DecisionCaseCreate,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    _limit_job(access)

    requested_ids = list(dict.fromkeys(body.evidence_ids))
    if len(requested_ids) > settings.decision_case_max_evidence:
        raise HTTPException(
            status_code=400,
            detail="Decision Case exceeds the configured evidence limit.",
        )

    if requested_ids:
        records = db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.tenant_id == access.tenant_id,
                EvidenceRecord.workspace_id == access.workspace_id,
                EvidenceRecord.id.in_(requested_ids),
            )
        ).all()
        found = {record.id: record for record in records}
        missing = [item for item in requested_ids if item not in found]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={"code": "unknown_evidence_ids", "evidence_ids": missing},
            )
        inaccessible = [
            record.id
            for record in records
            if not clearance_allows(access.data_clearance, record.classification)
        ]
        if inaccessible:
            raise HTTPException(
                status_code=403,
                detail="One or more requested evidence records exceed membership clearance.",
            )

    case = DecisionCase(
        id=f"DC-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        business_question=body.business_question,
        owner=body.owner,
        materiality=body.materiality,
        max_classification=access.data_clearance,
        status="queued",
        approval_state="not_reviewed",
        requested_evidence_ids=requested_ids,
        evidence_ids=[],
    )
    db.add(case)
    db.flush()
    job = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="decision_case_analyze",
        payload={"decision_case_id": case.id},
        settings=settings,
    )
    case.job_id = job.id
    append_audit_event(
        db,
        access,
        event_type="decision_case_queued",
        object_type="decision_case",
        object_id=case.id,
        detail={
            "materiality": case.materiality,
            "job_id": job.id,
            "requested_evidence_count": len(requested_ids),
        },
    )
    db.commit()
    return {"decision_case_id": case.id, "job_id": job.id}


@router.get("/v1/workspaces/{workspace_id}/decision-cases/{case_id}")
def get_decision_case(
    case_id: str,
    access: ViewerAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    case = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == access.tenant_id,
            DecisionCase.workspace_id == access.workspace_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Decision Case was not found.")
    if not clearance_allows(access.data_clearance, case.max_classification):
        raise HTTPException(status_code=403, detail="Decision Case clearance is required.")

    runs = db.scalars(
        select(AITeamRun)
        .where(
            AITeamRun.tenant_id == access.tenant_id,
            AITeamRun.workspace_id == access.workspace_id,
            AITeamRun.decision_case_id == case.id,
        )
        .order_by(AITeamRun.completed_at.asc())
    ).all()
    result = _case_payload(case)
    result["team_runs"] = [
        {
            "team_run_id": run.id,
            "team": run.team,
            "status": run.status,
            "evidence_ids": run.evidence_ids,
            "finding": run.finding,
            "method": run.method,
            "limitations": run.limitations,
            "completed_at": run.completed_at,
        }
        for run in runs
    ]
    return result


@router.post(
    "/v1/workspaces/{workspace_id}/decision-cases/{case_id}/rerun",
    status_code=status.HTTP_202_ACCEPTED,
)
def rerun_decision_case(
    case_id: str,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    _limit_job(access)
    case = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == access.tenant_id,
            DecisionCase.workspace_id == access.workspace_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Decision Case was not found.")
    if not clearance_allows(access.data_clearance, case.max_classification):
        raise HTTPException(status_code=403, detail="Decision Case clearance is required.")

    case.status = "queued"
    case.approval_state = "not_reviewed"
    case.approved_by = None
    case.approved_at = None
    case.review_rationale = None
    job = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="decision_case_analyze",
        payload={"decision_case_id": case.id},
        settings=settings,
    )
    case.job_id = job.id
    append_audit_event(
        db,
        access,
        event_type="decision_case_rerun_queued",
        object_type="decision_case",
        object_id=case.id,
        detail={"job_id": job.id},
    )
    db.commit()
    return {"decision_case_id": case.id, "job_id": job.id}


@router.post("/v1/workspaces/{workspace_id}/decision-cases/{case_id}/review")
def review_decision_case(
    case_id: str,
    body: DecisionCaseReview,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    case = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == access.tenant_id,
            DecisionCase.workspace_id == access.workspace_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Decision Case was not found.")
    if not clearance_allows(access.data_clearance, case.max_classification):
        raise HTTPException(status_code=403, detail="Decision Case clearance is required.")
    if case.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Only completed evidence-grounded Decision Cases can be reviewed.",
        )

    governance = db.scalar(
        select(AITeamRun).where(
            AITeamRun.tenant_id == access.tenant_id,
            AITeamRun.workspace_id == access.workspace_id,
            AITeamRun.decision_case_id == case.id,
            AITeamRun.team == "governance",
        )
    )
    if governance is None or governance.finding.get("review_ready") is not True:
        raise HTTPException(
            status_code=409,
            detail="Governance has not marked this Decision Case as review-ready.",
        )

    case.review_rationale = body.rationale
    case.approved_by = access.user_id
    case.approved_at = datetime.now(UTC)
    if body.action == "approve":
        case.approval_state = "approved_for_human_decision"
        event_type = "decision_case_review_approved"
    else:
        case.approval_state = "rejected"
        event_type = "decision_case_review_rejected"

    append_audit_event(
        db,
        access,
        event_type=event_type,
        object_type="decision_case",
        object_id=case.id,
        detail={
            "approval_state": case.approval_state,
            "rationale": body.rationale,
        },
    )
    db.commit()
    return {
        "decision_case_id": case.id,
        "approval_state": case.approval_state,
    }


@router.post(
    "/v1/workspaces/{workspace_id}/decision-cases/{case_id}/promote",
    status_code=status.HTTP_201_CREATED,
)
def promote_decision_case(
    case_id: str,
    body: DecisionPromotionInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    case = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == access.tenant_id,
            DecisionCase.workspace_id == access.workspace_id,
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Decision Case was not found.")
    if not clearance_allows(access.data_clearance, case.max_classification):
        raise HTTPException(status_code=403, detail="Decision Case clearance is required.")
    if case.approval_state != "approved_for_human_decision":
        raise HTTPException(
            status_code=409,
            detail="Decision Case requires Manager/Admin review approval before promotion.",
        )

    decision = DecisionRecord(
        id=f"DEC-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        owner=case.owner,
        status="approved_for_bounded_validation",
        payload={
            "decision_case_id": case.id,
            "selected_action": body.selected_action,
            "expected_outcome": body.expected_outcome,
            "alternative_considered": body.alternative_considered,
            "review_date": body.review_date.isoformat(),
            "linked_evidence_ids": case.evidence_ids,
            "participating_ai_teams": case.participating_teams,
            "control_plane_method": case.synthesis.get("method"),
            "causal_status": "causal-not-established",
            "human_approved": True,
        },
    )
    db.add(decision)
    db.flush()
    add_evidence_edge(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        source_type="decision_case",
        source_id=case.id,
        target_type="decision",
        target_id=decision.id,
        relation="promoted_to",
        classification=case.max_classification,
    )
    case.approval_state = "decision_recorded"
    append_audit_event(
        db,
        access,
        event_type="decision_case_promoted",
        object_type="decision",
        object_id=decision.id,
        detail={
            "decision_case_id": case.id,
            "owner": case.owner,
            "review_date": body.review_date.isoformat(),
        },
    )
    db.commit()
    return {"decision_case_id": case.id, "decision_id": decision.id}

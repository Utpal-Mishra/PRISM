from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.artifacts import append_artifact_version
from enterprise.audit import append_audit_event
from enterprise.db import get_db
from enterprise.models import DecisionRecord, OutcomeRecord, StrategyRecord
from enterprise.phase18_models import (
    ArtifactVersion,
    DatasetRegistryRecord,
    GovernanceRecord,
    MetricRegistryRecord,
)
from enterprise.tenancy import WorkspaceAccess, clearance_allows, require_role

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]
ViewerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("viewer"))]
AnalystAccessDep = Annotated[WorkspaceAccess, Depends(require_role("analyst"))]
ManagerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("manager"))]
AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role("admin"))]

Classification = Literal["public", "internal", "confidential", "restricted"]


class DatasetRegistryInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    owner: str = Field(min_length=1, max_length=255)
    steward: str = Field(default="", max_length=255)
    definition: str = Field(min_length=8, max_length=4000)
    cadence: str = Field(default="", max_length=100)
    certification: str = Field(default="draft", max_length=32)
    classification: Classification = "internal"
    source_asset_id: str | None = Field(default=None, max_length=96)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    status: str = Field(default="active", max_length=32)
    change_note: str = Field(default="", max_length=500)


class MetricRegistryInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    definition: str = Field(min_length=8, max_length=4000)
    formula: str = Field(min_length=1, max_length=4000)
    owner: str = Field(min_length=1, max_length=255)
    certification: str = Field(default="draft", max_length=32)
    classification: Classification = "internal"
    dataset_ids: list[str] = Field(default_factory=list, max_length=50)
    aliases: list[str] = Field(default_factory=list, max_length=50)
    status: str = Field(default="active", max_length=32)
    change_note: str = Field(default="", max_length=500)


class StrategyInput(BaseModel):
    classification: Classification = "internal"
    payload: dict[str, Any]
    change_note: str = Field(default="", max_length=500)


class DecisionUpdateInput(BaseModel):
    owner: str = Field(min_length=1, max_length=255)
    status: str = Field(min_length=1, max_length=64)
    classification: Classification = "internal"
    payload: dict[str, Any]
    change_note: str = Field(default="", max_length=500)


class OutcomeInput(BaseModel):
    decision_id: str = Field(min_length=1, max_length=96)
    classification: Classification = "internal"
    payload: dict[str, Any]
    change_note: str = Field(default="", max_length=500)


class GovernanceInput(BaseModel):
    control_area: str = Field(min_length=1, max_length=100)
    owner: str = Field(min_length=1, max_length=255)
    classification: Classification = "internal"
    status: str = Field(default="open", max_length=48)
    payload: dict[str, Any] = Field(default_factory=dict)
    change_note: str = Field(default="", max_length=500)


def _require_clearance(access: WorkspaceAccess, classification: str) -> None:
    if not clearance_allows(access.data_clearance, classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership data clearance does not allow this classification.",
        )


def _version_payload(record: Any, fields: list[str]) -> dict[str, Any]:
    return {field: getattr(record, field) for field in fields}


@router.get("/v1/workspaces/{workspace_id}/registry/datasets")
def list_datasets(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DatasetRegistryRecord)
        .where(
            DatasetRegistryRecord.tenant_id == access.tenant_id,
            DatasetRegistryRecord.workspace_id == access.workspace_id,
        )
        .order_by(DatasetRegistryRecord.name.asc())
    ).all()
    return [
        _version_payload(
            row,
            [
                "id",
                "name",
                "owner",
                "steward",
                "definition",
                "cadence",
                "certification",
                "classification",
                "source_asset_id",
                "aliases",
                "status",
                "version",
                "updated_at",
            ],
        )
        for row in rows
        if clearance_allows(access.data_clearance, row.classification)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/registry/datasets",
    status_code=status.HTTP_201_CREATED,
)
def create_dataset(
    body: DatasetRegistryInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    record = DatasetRegistryRecord(
        id=f"DS-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(exclude={"change_note"}),
    )
    db.add(record)
    db.flush()
    payload = _version_payload(
        record,
        [
            "name",
            "owner",
            "steward",
            "definition",
            "cadence",
            "certification",
            "classification",
            "source_asset_id",
            "aliases",
            "status",
        ],
    )
    version = append_artifact_version(
        db,
        access,
        artifact_type="dataset_registry",
        artifact_id=record.id,
        classification=record.classification,
        payload=payload,
        change_note=body.change_note or "Initial dataset registry record.",
    )
    append_audit_event(
        db,
        access,
        event_type="dataset_registry_created",
        object_type="dataset_registry",
        object_id=record.id,
        detail={"version": version.version, "certification": record.certification},
    )
    db.commit()
    return {"dataset_id": record.id, "version": version.version}


@router.put("/v1/workspaces/{workspace_id}/registry/datasets/{dataset_id}")
def update_dataset(
    dataset_id: str,
    body: DatasetRegistryInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    record = db.scalar(
        select(DatasetRegistryRecord)
        .where(
            DatasetRegistryRecord.id == dataset_id,
            DatasetRegistryRecord.tenant_id == access.tenant_id,
            DatasetRegistryRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset registry record was not found.")
    for key, value in body.model_dump(exclude={"change_note"}).items():
        setattr(record, key, value)
    record.version += 1
    payload = _version_payload(
        record,
        [
            "name",
            "owner",
            "steward",
            "definition",
            "cadence",
            "certification",
            "classification",
            "source_asset_id",
            "aliases",
            "status",
        ],
    )
    version = append_artifact_version(
        db,
        access,
        artifact_type="dataset_registry",
        artifact_id=record.id,
        classification=record.classification,
        payload=payload,
        change_note=body.change_note or "Dataset registry record updated.",
    )
    db.commit()
    return {"dataset_id": record.id, "version": version.version}


@router.get("/v1/workspaces/{workspace_id}/registry/metrics")
def list_metrics(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(MetricRegistryRecord)
        .where(
            MetricRegistryRecord.tenant_id == access.tenant_id,
            MetricRegistryRecord.workspace_id == access.workspace_id,
        )
        .order_by(MetricRegistryRecord.name.asc())
    ).all()
    return [
        _version_payload(
            row,
            [
                "id",
                "name",
                "definition",
                "formula",
                "owner",
                "certification",
                "classification",
                "dataset_ids",
                "aliases",
                "status",
                "version",
                "updated_at",
            ],
        )
        for row in rows
        if clearance_allows(access.data_clearance, row.classification)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/registry/metrics",
    status_code=status.HTTP_201_CREATED,
)
def create_metric(
    body: MetricRegistryInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    record = MetricRegistryRecord(
        id=f"MET-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(exclude={"change_note"}),
    )
    db.add(record)
    db.flush()
    payload = _version_payload(
        record,
        [
            "name",
            "definition",
            "formula",
            "owner",
            "certification",
            "classification",
            "dataset_ids",
            "aliases",
            "status",
        ],
    )
    version = append_artifact_version(
        db,
        access,
        artifact_type="metric_registry",
        artifact_id=record.id,
        classification=record.classification,
        payload=payload,
        change_note=body.change_note or "Initial metric registry record.",
    )
    append_audit_event(
        db,
        access,
        event_type="metric_registry_created",
        object_type="metric_registry",
        object_id=record.id,
        detail={"version": version.version, "certification": record.certification},
    )
    db.commit()
    return {"metric_id": record.id, "version": version.version}


@router.put("/v1/workspaces/{workspace_id}/registry/metrics/{metric_id}")
def update_metric(
    metric_id: str,
    body: MetricRegistryInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    record = db.scalar(
        select(MetricRegistryRecord)
        .where(
            MetricRegistryRecord.id == metric_id,
            MetricRegistryRecord.tenant_id == access.tenant_id,
            MetricRegistryRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Metric registry record was not found.")
    for key, value in body.model_dump(exclude={"change_note"}).items():
        setattr(record, key, value)
    record.version += 1
    payload = _version_payload(
        record,
        [
            "name",
            "definition",
            "formula",
            "owner",
            "certification",
            "classification",
            "dataset_ids",
            "aliases",
            "status",
        ],
    )
    version = append_artifact_version(
        db,
        access,
        artifact_type="metric_registry",
        artifact_id=record.id,
        classification=record.classification,
        payload=payload,
        change_note=body.change_note or "Metric registry record updated.",
    )
    db.commit()
    return {"metric_id": record.id, "version": version.version}


@router.get("/v1/workspaces/{workspace_id}/strategies")
def list_strategies(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(StrategyRecord)
        .where(
            StrategyRecord.tenant_id == access.tenant_id,
            StrategyRecord.workspace_id == access.workspace_id,
        )
        .order_by(StrategyRecord.created_at.desc())
    ).all()
    return [
        {
            "strategy_id": row.id,
            "payload": row.payload,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/strategies",
    status_code=status.HTTP_201_CREATED,
)
def create_strategy(
    body: StrategyInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    strategy = StrategyRecord(
        id=f"STR-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        payload={**body.payload, "classification": body.classification},
    )
    db.add(strategy)
    db.flush()
    version = append_artifact_version(
        db,
        access,
        artifact_type="strategy",
        artifact_id=strategy.id,
        classification=body.classification,
        payload=strategy.payload,
        change_note=body.change_note or "Initial strategy record.",
    )
    append_audit_event(
        db,
        access,
        event_type="strategy_created",
        object_type="strategy",
        object_id=strategy.id,
        detail={"version": version.version},
    )
    db.commit()
    return {"strategy_id": strategy.id, "version": version.version}


@router.put("/v1/workspaces/{workspace_id}/strategies/{strategy_id}")
def update_strategy(
    strategy_id: str,
    body: StrategyInput,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    strategy = db.scalar(
        select(StrategyRecord)
        .where(
            StrategyRecord.id == strategy_id,
            StrategyRecord.tenant_id == access.tenant_id,
            StrategyRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy record was not found.")
    strategy.payload = {**body.payload, "classification": body.classification}
    version = append_artifact_version(
        db,
        access,
        artifact_type="strategy",
        artifact_id=strategy.id,
        classification=body.classification,
        payload=strategy.payload,
        change_note=body.change_note or "Strategy record updated.",
    )
    db.commit()
    return {"strategy_id": strategy.id, "version": version.version}


@router.get("/v1/workspaces/{workspace_id}/decisions")
def list_decisions(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DecisionRecord)
        .where(
            DecisionRecord.tenant_id == access.tenant_id,
            DecisionRecord.workspace_id == access.workspace_id,
        )
        .order_by(DecisionRecord.created_at.desc())
    ).all()
    result: list[dict[str, Any]] = []
    for row in rows:
        classification = str(row.payload.get("classification", "internal"))
        if not clearance_allows(access.data_clearance, classification):
            continue
        result.append(
            {
                "decision_id": row.id,
                "owner": row.owner,
                "status": row.status,
                "classification": classification,
                "payload": row.payload,
                "created_at": row.created_at,
            }
        )
    return result


@router.put("/v1/workspaces/{workspace_id}/decisions/{decision_id}")
def update_decision(
    decision_id: str,
    body: DecisionUpdateInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    decision = db.scalar(
        select(DecisionRecord)
        .where(
            DecisionRecord.id == decision_id,
            DecisionRecord.tenant_id == access.tenant_id,
            DecisionRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision record was not found.")
    decision.owner = body.owner
    decision.status = body.status
    decision.payload = {**body.payload, "classification": body.classification}
    version = append_artifact_version(
        db,
        access,
        artifact_type="decision",
        artifact_id=decision.id,
        classification=body.classification,
        payload={
            "owner": decision.owner,
            "status": decision.status,
            "payload": decision.payload,
        },
        change_note=body.change_note or "Decision record updated.",
    )
    append_audit_event(
        db,
        access,
        event_type="decision_updated",
        object_type="decision",
        object_id=decision.id,
        detail={"version": version.version, "status": decision.status},
    )
    db.commit()
    return {"decision_id": decision.id, "version": version.version}


@router.get("/v1/workspaces/{workspace_id}/outcomes")
def list_outcomes(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(OutcomeRecord)
        .where(
            OutcomeRecord.tenant_id == access.tenant_id,
            OutcomeRecord.workspace_id == access.workspace_id,
        )
        .order_by(OutcomeRecord.created_at.desc())
    ).all()
    return [
        {
            "outcome_id": row.id,
            "decision_id": row.decision_id,
            "payload": row.payload,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/outcomes",
    status_code=status.HTTP_201_CREATED,
)
def create_outcome(
    body: OutcomeInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    decision = db.scalar(
        select(DecisionRecord).where(
            DecisionRecord.id == body.decision_id,
            DecisionRecord.tenant_id == access.tenant_id,
            DecisionRecord.workspace_id == access.workspace_id,
        )
    )
    if decision is None:
        raise HTTPException(status_code=404, detail="Linked decision was not found.")
    outcome = OutcomeRecord(
        id=f"OUT-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        decision_id=body.decision_id,
        payload={**body.payload, "classification": body.classification},
    )
    db.add(outcome)
    db.flush()
    version = append_artifact_version(
        db,
        access,
        artifact_type="outcome",
        artifact_id=outcome.id,
        classification=body.classification,
        payload=outcome.payload,
        change_note=body.change_note or "Initial outcome record.",
    )
    append_audit_event(
        db,
        access,
        event_type="outcome_created",
        object_type="outcome",
        object_id=outcome.id,
        detail={"decision_id": outcome.decision_id, "version": version.version},
    )
    db.commit()
    return {"outcome_id": outcome.id, "version": version.version}


@router.put("/v1/workspaces/{workspace_id}/outcomes/{outcome_id}")
def update_outcome(
    outcome_id: str,
    body: OutcomeInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    outcome = db.scalar(
        select(OutcomeRecord)
        .where(
            OutcomeRecord.id == outcome_id,
            OutcomeRecord.tenant_id == access.tenant_id,
            OutcomeRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if outcome is None:
        raise HTTPException(status_code=404, detail="Outcome record was not found.")
    outcome.decision_id = body.decision_id
    outcome.payload = {**body.payload, "classification": body.classification}
    version = append_artifact_version(
        db,
        access,
        artifact_type="outcome",
        artifact_id=outcome.id,
        classification=body.classification,
        payload=outcome.payload,
        change_note=body.change_note or "Outcome record updated.",
    )
    db.commit()
    return {"outcome_id": outcome.id, "version": version.version}


@router.get("/v1/workspaces/{workspace_id}/governance")
def list_governance(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(GovernanceRecord)
        .where(
            GovernanceRecord.tenant_id == access.tenant_id,
            GovernanceRecord.workspace_id == access.workspace_id,
        )
        .order_by(GovernanceRecord.updated_at.desc())
    ).all()
    return [
        _version_payload(
            row,
            [
                "id",
                "control_area",
                "owner",
                "classification",
                "status",
                "payload",
                "version",
                "updated_at",
            ],
        )
        for row in rows
        if clearance_allows(access.data_clearance, row.classification)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/governance",
    status_code=status.HTTP_201_CREATED,
)
def create_governance(
    body: GovernanceInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    record = GovernanceRecord(
        id=f"GOV-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(exclude={"change_note"}),
    )
    db.add(record)
    db.flush()
    version = append_artifact_version(
        db,
        access,
        artifact_type="governance",
        artifact_id=record.id,
        classification=record.classification,
        payload={
            "control_area": record.control_area,
            "owner": record.owner,
            "status": record.status,
            "payload": record.payload,
        },
        change_note=body.change_note or "Initial governance record.",
    )
    append_audit_event(
        db,
        access,
        event_type="governance_record_created",
        object_type="governance",
        object_id=record.id,
        detail={"version": version.version, "control_area": record.control_area},
    )
    db.commit()
    return {"governance_id": record.id, "version": version.version}


@router.put("/v1/workspaces/{workspace_id}/governance/{governance_id}")
def update_governance(
    governance_id: str,
    body: GovernanceInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _require_clearance(access, body.classification)
    record = db.scalar(
        select(GovernanceRecord)
        .where(
            GovernanceRecord.id == governance_id,
            GovernanceRecord.tenant_id == access.tenant_id,
            GovernanceRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Governance record was not found.")
    for key, value in body.model_dump(exclude={"change_note"}).items():
        setattr(record, key, value)
    record.version += 1
    version = append_artifact_version(
        db,
        access,
        artifact_type="governance",
        artifact_id=record.id,
        classification=record.classification,
        payload={
            "control_area": record.control_area,
            "owner": record.owner,
            "status": record.status,
            "payload": record.payload,
        },
        change_note=body.change_note or "Governance record updated.",
    )
    db.commit()
    return {"governance_id": record.id, "version": version.version}


@router.get("/v1/workspaces/{workspace_id}/artifacts/{artifact_type}/{artifact_id}/versions")
def list_artifact_versions(
    artifact_type: str,
    artifact_id: str,
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(ArtifactVersion)
        .where(
            ArtifactVersion.tenant_id == access.tenant_id,
            ArtifactVersion.workspace_id == access.workspace_id,
            ArtifactVersion.artifact_type == artifact_type,
            ArtifactVersion.artifact_id == artifact_id,
        )
        .order_by(ArtifactVersion.version.desc())
    ).all()
    return [
        {
            "version": row.version,
            "classification": row.classification,
            "payload": row.payload,
            "content_hash": row.content_hash,
            "change_note": row.change_note,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }
        for row in rows
        if clearance_allows(access.data_clearance, row.classification)
    ]

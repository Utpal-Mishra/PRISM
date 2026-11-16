from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event
from enterprise.db import get_db
from enterprise.phase18_models import (
    DataResidencyPolicy,
    DPARecord,
    DPIAAssessment,
    IncidentRecord,
    LegalHold,
    ProcessingActivity,
)
from enterprise.tenancy import WorkspaceAccess, require_role

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]
ManagerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("manager"))]
AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role("admin"))]


class ProcessingActivityInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=8, max_length=4000)
    lawful_basis: str = Field(min_length=2, max_length=120)
    data_categories: list[str] = Field(default_factory=list, max_length=50)
    data_subjects: list[str] = Field(default_factory=list, max_length=50)
    recipients: list[str] = Field(default_factory=list, max_length=50)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    residency_regions: list[str] = Field(default_factory=list, max_length=30)
    owner: str = Field(min_length=1, max_length=255)
    status: str = Field(default="active", max_length=32)


class DPIAInput(BaseModel):
    processing_activity_id: str = Field(min_length=1, max_length=96)
    risk_level: Literal["low", "medium", "high", "very_high"]
    necessity: str = Field(min_length=8, max_length=4000)
    proportionality: str = Field(min_length=8, max_length=4000)
    risks: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    mitigations: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    residual_risk: Literal["low", "medium", "high", "very_high"]
    reviewer: str = Field(min_length=1, max_length=255)
    status: Literal["draft", "approved", "rejected", "review_required"] = "draft"


class DPAInput(BaseModel):
    counterparty: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=64)
    effective_date: str = Field(min_length=8, max_length=32)
    expiry_date: str | None = Field(default=None, max_length=32)
    transfer_mechanism: str = Field(default="", max_length=120)
    subprocessor_terms: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="active", max_length=32)


class ResidencyPolicyInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    allowed_regions: list[str] = Field(min_length=1, max_length=30)
    prohibited_regions: list[str] = Field(default_factory=list, max_length=30)
    classification_ceiling: Literal[
        "public",
        "internal",
        "confidential",
        "restricted",
    ] = "restricted"
    cross_border_basis: str = Field(default="", max_length=200)
    status: str = Field(default="active", max_length=32)


class IncidentInput(BaseModel):
    severity: Literal["sev1", "sev2", "sev3", "sev4"]
    category: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=8, max_length=4000)
    owner: str = Field(min_length=1, max_length=255)
    notification_required: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class IncidentStatusInput(BaseModel):
    status: Literal["open", "contained", "resolved"]
    note: str = Field(min_length=4, max_length=1000)


class LegalHoldInput(BaseModel):
    scope_type: str = Field(min_length=1, max_length=64)
    scope_id: str = Field(min_length=1, max_length=96)
    reason: str = Field(min_length=8, max_length=500)


def _list_rows(db: Session, model: Any, access: WorkspaceAccess) -> list[Any]:
    return db.scalars(
        select(model)
        .where(
            model.tenant_id == access.tenant_id,
            model.workspace_id == access.workspace_id,
        )
        .order_by(model.created_at.desc())
        .limit(500)
    ).all()


@router.get("/v1/workspaces/{workspace_id}/privacy/processing-activities")
def list_processing_activities(
    access: ManagerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    return [
        {
            "processing_activity_id": row.id,
            "name": row.name,
            "purpose": row.purpose,
            "lawful_basis": row.lawful_basis,
            "data_categories": row.data_categories,
            "data_subjects": row.data_subjects,
            "recipients": row.recipients,
            "retention_days": row.retention_days,
            "residency_regions": row.residency_regions,
            "owner": row.owner,
            "status": row.status,
            "updated_at": row.updated_at,
        }
        for row in _list_rows(db, ProcessingActivity, access)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/privacy/processing-activities",
    status_code=status.HTTP_201_CREATED,
)
def create_processing_activity(
    body: ProcessingActivityInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    record = ProcessingActivity(
        id=f"ROPA-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="processing_activity_created",
        object_type="processing_activity",
        object_id=record.id,
        detail={"lawful_basis": record.lawful_basis, "owner": record.owner},
    )
    db.commit()
    return {"processing_activity_id": record.id}


@router.post(
    "/v1/workspaces/{workspace_id}/privacy/dpia",
    status_code=status.HTTP_201_CREATED,
)
def create_dpia(
    body: DPIAInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    activity = db.scalar(
        select(ProcessingActivity).where(
            ProcessingActivity.id == body.processing_activity_id,
            ProcessingActivity.tenant_id == access.tenant_id,
            ProcessingActivity.workspace_id == access.workspace_id,
        )
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Processing activity was not found.")
    record = DPIAAssessment(
        id=f"DPIA-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
        reviewed_at=datetime.now(UTC) if body.status == "approved" else None,
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="dpia_created",
        object_type="dpia",
        object_id=record.id,
        detail={
            "processing_activity_id": record.processing_activity_id,
            "risk_level": record.risk_level,
            "residual_risk": record.residual_risk,
            "status": record.status,
        },
    )
    db.commit()
    return {"dpia_id": record.id}


@router.get("/v1/workspaces/{workspace_id}/privacy/dpia")
def list_dpia(
    access: ManagerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    return [
        {
            "dpia_id": row.id,
            "processing_activity_id": row.processing_activity_id,
            "risk_level": row.risk_level,
            "residual_risk": row.residual_risk,
            "reviewer": row.reviewer,
            "status": row.status,
            "reviewed_at": row.reviewed_at,
        }
        for row in _list_rows(db, DPIAAssessment, access)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/privacy/dpas",
    status_code=status.HTTP_201_CREATED,
)
def create_dpa(
    body: DPAInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    record = DPARecord(
        id=f"DPA-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
    )
    db.add(record)
    db.commit()
    return {"dpa_id": record.id}


@router.get("/v1/workspaces/{workspace_id}/privacy/dpas")
def list_dpas(
    access: ManagerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    return [
        {
            "dpa_id": row.id,
            "counterparty": row.counterparty,
            "role": row.role,
            "effective_date": row.effective_date,
            "expiry_date": row.expiry_date,
            "transfer_mechanism": row.transfer_mechanism,
            "status": row.status,
        }
        for row in _list_rows(db, DPARecord, access)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/privacy/residency-policies",
    status_code=status.HTTP_201_CREATED,
)
def create_residency_policy(
    body: ResidencyPolicyInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    overlap = set(body.allowed_regions).intersection(body.prohibited_regions)
    if overlap:
        raise HTTPException(
            status_code=400,
            detail={"code": "residency_region_conflict", "regions": sorted(overlap)},
        )
    record = DataResidencyPolicy(
        id=f"RES-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
    )
    db.add(record)
    db.commit()
    return {"residency_policy_id": record.id}


@router.get("/v1/workspaces/{workspace_id}/privacy/residency-policies")
def list_residency_policies(
    access: ManagerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    return [
        {
            "residency_policy_id": row.id,
            "name": row.name,
            "allowed_regions": row.allowed_regions,
            "prohibited_regions": row.prohibited_regions,
            "classification_ceiling": row.classification_ceiling,
            "cross_border_basis": row.cross_border_basis,
            "status": row.status,
        }
        for row in _list_rows(db, DataResidencyPolicy, access)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/incidents",
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    body: IncidentInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    record = IncidentRecord(
        id=f"INC-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
        status="open",
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="incident_opened",
        object_type="incident",
        object_id=record.id,
        detail={"severity": record.severity, "category": record.category},
    )
    db.commit()
    return {"incident_id": record.id}


@router.post("/v1/workspaces/{workspace_id}/incidents/{incident_id}/status")
def update_incident_status(
    incident_id: str,
    body: IncidentStatusInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    record = db.scalar(
        select(IncidentRecord)
        .where(
            IncidentRecord.id == incident_id,
            IncidentRecord.tenant_id == access.tenant_id,
            IncidentRecord.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Incident was not found.")
    record.status = body.status
    now = datetime.now(UTC)
    if body.status == "contained":
        record.contained_at = now
    if body.status == "resolved":
        record.resolved_at = now
    append_audit_event(
        db,
        access,
        event_type=f"incident_{body.status}",
        object_type="incident",
        object_id=record.id,
        detail={"note": body.note},
    )
    db.commit()
    return {"incident_id": record.id, "status": record.status}


@router.get("/v1/workspaces/{workspace_id}/incidents")
def list_incidents(
    access: ManagerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    return [
        {
            "incident_id": row.id,
            "severity": row.severity,
            "category": row.category,
            "summary": row.summary,
            "status": row.status,
            "owner": row.owner,
            "detected_at": row.detected_at,
            "contained_at": row.contained_at,
            "resolved_at": row.resolved_at,
            "notification_required": row.notification_required,
        }
        for row in _list_rows(db, IncidentRecord, access)
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/legal-holds",
    status_code=status.HTTP_201_CREATED,
)
def create_legal_hold(
    body: LegalHoldInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    hold = LegalHold(
        id=f"HOLD-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
        status="active",
    )
    db.add(hold)
    append_audit_event(
        db,
        access,
        event_type="legal_hold_created",
        object_type="legal_hold",
        object_id=hold.id,
        detail={"scope_type": hold.scope_type, "scope_id": hold.scope_id},
    )
    db.commit()
    return {"legal_hold_id": hold.id}


@router.post("/v1/workspaces/{workspace_id}/legal-holds/{hold_id}/release")
def release_legal_hold(
    hold_id: str,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    hold = db.scalar(
        select(LegalHold)
        .where(
            LegalHold.id == hold_id,
            LegalHold.tenant_id == access.tenant_id,
            LegalHold.workspace_id == access.workspace_id,
            LegalHold.status == "active",
        )
        .with_for_update()
    )
    if hold is None:
        raise HTTPException(status_code=404, detail="Active legal hold was not found.")
    hold.status = "released"
    hold.released_at = datetime.now(UTC)
    append_audit_event(
        db,
        access,
        event_type="legal_hold_released",
        object_type="legal_hold",
        object_id=hold.id,
        detail={"scope_type": hold.scope_type, "scope_id": hold.scope_id},
    )
    db.commit()
    return {"legal_hold_id": hold.id, "status": hold.status}

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event
from enterprise.config import get_settings
from enterprise.db import get_db
from enterprise.models import EvidenceRecord
from enterprise.observability import PILOT_EVENTS
from enterprise.phase18_models import EnterprisePilot, PilotMeasurement, UATFinding
from enterprise.tenancy import WorkspaceAccess, require_role

router = APIRouter()
settings = get_settings()
DbDep = Annotated[Session, Depends(get_db)]
ManagerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("manager"))]
AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role("admin"))]


class PilotInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    organisation_label: str = Field(min_length=1, max_length=200)
    owner: str = Field(min_length=1, max_length=255)
    start_date: str = Field(min_length=8, max_length=32)
    end_date: str = Field(min_length=8, max_length=32)
    user_limit: int = Field(ge=1, le=100)
    data_domains: list[str] = Field(min_length=1, max_length=20)
    allowed_classifications: list[
        Literal["public", "internal", "confidential", "restricted"]
    ] = Field(min_length=1, max_length=4)
    success_criteria: dict[str, Any]
    status: Literal["planned", "active", "paused", "completed"] = "planned"


class PilotGateInput(BaseModel):
    security_review_status: Literal["pending", "passed", "failed"]
    uat_status: Literal["pending", "passed", "failed"]


class PilotMeasurementInput(BaseModel):
    metric: str = Field(min_length=1, max_length=160)
    target: float | None = None
    actual: float | None = None
    unit: str = Field(default="", max_length=64)
    evidence_id: str | None = Field(default=None, max_length=96)


class UATFindingInput(BaseModel):
    severity: Literal["critical", "high", "medium", "low"]
    area: str = Field(min_length=1, max_length=100)
    finding: str = Field(min_length=8, max_length=4000)
    owner: str = Field(min_length=1, max_length=255)


@router.get("/v1/workspaces/{workspace_id}/pilots")
def list_pilots(
    access: ManagerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(EnterprisePilot)
        .where(
            EnterprisePilot.tenant_id == access.tenant_id,
            EnterprisePilot.workspace_id == access.workspace_id,
        )
        .order_by(EnterprisePilot.created_at.desc())
    ).all()
    return [
        {
            "pilot_id": row.id,
            "name": row.name,
            "organisation_label": row.organisation_label,
            "owner": row.owner,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "user_limit": row.user_limit,
            "data_domains": row.data_domains,
            "allowed_classifications": row.allowed_classifications,
            "success_criteria": row.success_criteria,
            "status": row.status,
            "security_review_status": row.security_review_status,
            "uat_status": row.uat_status,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@router.post(
    "/v1/workspaces/{workspace_id}/pilots",
    status_code=status.HTTP_201_CREATED,
)
def create_pilot(
    body: PilotInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    if body.user_limit > settings.pilot_max_users:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Pilot user_limit exceeds configured maximum "
                f"of {settings.pilot_max_users}."
            ),
        )
    pilot = EnterprisePilot(
        id=f"PILOT-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        **body.model_dump(),
        security_review_status="pending",
        uat_status="pending",
    )
    db.add(pilot)
    PILOT_EVENTS.labels(event="created").inc()
    append_audit_event(
        db,
        access,
        event_type="enterprise_pilot_created",
        object_type="enterprise_pilot",
        object_id=pilot.id,
        detail={
            "user_limit": pilot.user_limit,
            "data_domains": pilot.data_domains,
            "allowed_classifications": pilot.allowed_classifications,
        },
    )
    db.commit()
    return {"pilot_id": pilot.id}


@router.post("/v1/workspaces/{workspace_id}/pilots/{pilot_id}/gates")
def update_pilot_gates(
    pilot_id: str,
    body: PilotGateInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    pilot = db.scalar(
        select(EnterprisePilot)
        .where(
            EnterprisePilot.id == pilot_id,
            EnterprisePilot.tenant_id == access.tenant_id,
            EnterprisePilot.workspace_id == access.workspace_id,
        )
        .with_for_update()
    )
    if pilot is None:
        raise HTTPException(status_code=404, detail="Enterprise pilot was not found.")
    pilot.security_review_status = body.security_review_status
    pilot.uat_status = body.uat_status
    if (
        pilot.status == "planned"
        and body.security_review_status == "passed"
        and body.uat_status == "passed"
    ):
        pilot.status = "active"
    PILOT_EVENTS.labels(event="gates_updated").inc()
    append_audit_event(
        db,
        access,
        event_type="enterprise_pilot_gates_updated",
        object_type="enterprise_pilot",
        object_id=pilot.id,
        detail={
            "security_review_status": pilot.security_review_status,
            "uat_status": pilot.uat_status,
            "status": pilot.status,
        },
    )
    db.commit()
    return {
        "pilot_id": pilot.id,
        "status": pilot.status,
        "security_review_status": pilot.security_review_status,
        "uat_status": pilot.uat_status,
    }


@router.post(
    "/v1/workspaces/{workspace_id}/pilots/{pilot_id}/measurements",
    status_code=status.HTTP_201_CREATED,
)
def record_pilot_measurement(
    pilot_id: str,
    body: PilotMeasurementInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    pilot = db.scalar(
        select(EnterprisePilot).where(
            EnterprisePilot.id == pilot_id,
            EnterprisePilot.tenant_id == access.tenant_id,
            EnterprisePilot.workspace_id == access.workspace_id,
        )
    )
    if pilot is None:
        raise HTTPException(status_code=404, detail="Enterprise pilot was not found.")
    if body.evidence_id:
        evidence = db.scalar(
            select(EvidenceRecord).where(
                EvidenceRecord.id == body.evidence_id,
                EvidenceRecord.tenant_id == access.tenant_id,
                EvidenceRecord.workspace_id == access.workspace_id,
            )
        )
        if evidence is None:
            raise HTTPException(status_code=404, detail="Pilot evidence was not found.")
    measurement = PilotMeasurement(
        id=f"PM-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        pilot_id=pilot.id,
        **body.model_dump(),
    )
    db.add(measurement)
    PILOT_EVENTS.labels(event="measurement_recorded").inc()
    db.commit()
    return {"pilot_measurement_id": measurement.id}


@router.post(
    "/v1/workspaces/{workspace_id}/pilots/{pilot_id}/uat-findings",
    status_code=status.HTTP_201_CREATED,
)
def create_uat_finding(
    pilot_id: str,
    body: UATFindingInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    pilot = db.scalar(
        select(EnterprisePilot).where(
            EnterprisePilot.id == pilot_id,
            EnterprisePilot.tenant_id == access.tenant_id,
            EnterprisePilot.workspace_id == access.workspace_id,
        )
    )
    if pilot is None:
        raise HTTPException(status_code=404, detail="Enterprise pilot was not found.")
    finding = UATFinding(
        id=f"UAT-{uuid.uuid4().hex.upper()}",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        pilot_id=pilot.id,
        **body.model_dump(),
        status="open",
    )
    db.add(finding)
    PILOT_EVENTS.labels(event="uat_finding_recorded").inc()
    if body.severity in {"critical", "high"}:
        pilot.uat_status = "failed"
    db.commit()
    return {"uat_finding_id": finding.id}


@router.get("/v1/workspaces/{workspace_id}/pilots/{pilot_id}/readiness")
def pilot_readiness(
    pilot_id: str,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    pilot = db.scalar(
        select(EnterprisePilot).where(
            EnterprisePilot.id == pilot_id,
            EnterprisePilot.tenant_id == access.tenant_id,
            EnterprisePilot.workspace_id == access.workspace_id,
        )
    )
    if pilot is None:
        raise HTTPException(status_code=404, detail="Enterprise pilot was not found.")
    findings = db.scalars(
        select(UATFinding).where(
            UATFinding.tenant_id == access.tenant_id,
            UATFinding.workspace_id == access.workspace_id,
            UATFinding.pilot_id == pilot.id,
            UATFinding.status == "open",
        )
    ).all()
    measurements = db.scalars(
        select(PilotMeasurement).where(
            PilotMeasurement.tenant_id == access.tenant_id,
            PilotMeasurement.workspace_id == access.workspace_id,
            PilotMeasurement.pilot_id == pilot.id,
        )
    ).all()
    blocking = [
        finding.id
        for finding in findings
        if finding.severity in {"critical", "high"}
    ]
    measured_metrics = {item.metric for item in measurements}
    expected_metrics = set(pilot.success_criteria.keys())
    missing_metrics = sorted(expected_metrics - measured_metrics)
    ready = (
        pilot.security_review_status == "passed"
        and pilot.uat_status == "passed"
        and not blocking
        and not missing_metrics
    )
    return {
        "pilot_id": pilot.id,
        "ready_for_completion": ready,
        "security_review_status": pilot.security_review_status,
        "uat_status": pilot.uat_status,
        "blocking_uat_findings": blocking,
        "missing_success_measurements": missing_metrics,
        "measured_metric_count": len(measured_metrics),
    }

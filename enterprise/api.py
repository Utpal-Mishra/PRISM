from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event, verify_audit_chain
from enterprise.config import get_settings
from enterprise.db import get_db
from enterprise.models import AuditEvent, DecisionRecord, EvidenceRecord
from enterprise.security import install_security_middleware
from enterprise.tenancy import (
    WorkspaceAccess,
    clearance_allows,
    get_workspace_access,
    require_role,
)

settings = get_settings()
app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None,
)
install_security_middleware(app, settings)


class EvidenceCreate(BaseModel):
    evidence_id: str | None = Field(default=None, max_length=96)
    evidence_class: str = Field(min_length=1, max_length=64)
    classification: str = Field(
        default="internal",
        pattern="^(public|internal|confidential|restricted)$",
    )
    payload: dict[str, Any]


class DecisionCreate(BaseModel):
    decision_id: str | None = Field(default=None, max_length=96)
    owner: str = Field(min_length=1, max_length=255)
    status: str = Field(
        default="approved_for_bounded_validation",
        max_length=64,
    )
    payload: dict[str, Any]


DbDep = Annotated[Session, Depends(get_db)]
AccessDep = Annotated[WorkspaceAccess, Depends(get_workspace_access)]
ViewerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("viewer"))]
AnalystAccessDep = Annotated[WorkspaceAccess, Depends(require_role("analyst"))]
ManagerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("manager"))]
AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role("admin"))]


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready(db: DbDep) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/v1/workspaces/{workspace_id}/me")
def workspace_me(access: AccessDep) -> dict[str, str | None]:
    return {
        "workspace_id": access.workspace_id,
        "tenant_id": access.tenant_id,
        "subject": access.principal.subject,
        "email": access.principal.email,
        "role": access.role,
        "data_clearance": access.data_clearance,
    }


@app.get("/v1/workspaces/{workspace_id}/evidence")
def list_evidence(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(EvidenceRecord)
        .where(
            EvidenceRecord.tenant_id == access.tenant_id,
            EvidenceRecord.workspace_id == access.workspace_id,
        )
        .order_by(EvidenceRecord.created_at.desc())
        .limit(200)
    ).all()
    return [
        {
            "evidence_id": row.id,
            "evidence_class": row.evidence_class,
            "classification": row.classification,
            "payload": row.payload,
            "created_at": row.created_at,
        }
        for row in rows
        if clearance_allows(access.data_clearance, row.classification)
    ]


@app.post(
    "/v1/workspaces/{workspace_id}/evidence",
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    body: EvidenceCreate,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, str]:
    if not clearance_allows(access.data_clearance, body.classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership data clearance does not allow this classification.",
        )

    evidence_id = body.evidence_id or f"EVD-{uuid.uuid4().hex.upper()}"
    record = EvidenceRecord(
        id=evidence_id,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        evidence_class=body.evidence_class,
        classification=body.classification,
        payload=body.payload,
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="evidence_created",
        object_type="evidence",
        object_id=record.id,
        detail={
            "classification": body.classification,
            "evidence_class": body.evidence_class,
        },
    )
    db.commit()
    return {"evidence_id": record.id}


@app.post(
    "/v1/workspaces/{workspace_id}/decisions",
    status_code=status.HTTP_201_CREATED,
)
def create_decision(
    body: DecisionCreate,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    decision_id = body.decision_id or f"DEC-{uuid.uuid4().hex.upper()}"
    record = DecisionRecord(
        id=decision_id,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        owner=body.owner,
        status=body.status,
        payload=body.payload,
    )
    db.add(record)
    append_audit_event(
        db,
        access,
        event_type="decision_created",
        object_type="decision",
        object_id=record.id,
        detail={
            "owner": body.owner,
            "status": body.status,
        },
    )
    db.commit()
    return {"decision_id": record.id}


@app.get("/v1/workspaces/{workspace_id}/audit")
def list_audit_events(
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    events = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == access.tenant_id,
            AuditEvent.workspace_id == access.workspace_id,
        )
        .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        .limit(1000)
    ).all()
    return {
        "chain_valid": verify_audit_chain(list(events)),
        "events": [
            {
                "audit_id": event.id,
                "event_type": event.event_type,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "actor_subject": event.actor_subject,
                "previous_hash": event.previous_hash,
                "event_hash": event.event_hash,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }

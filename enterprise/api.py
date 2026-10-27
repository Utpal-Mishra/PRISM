from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from enterprise.config import get_settings
from enterprise.db import get_db
from enterprise.models import DecisionRecord, EvidenceRecord
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


class EvidenceCreate(BaseModel):
    evidence_id: str | None = Field(default=None, max_length=96)
    evidence_class: str = Field(min_length=1, max_length=64)
    classification: str = Field(default="internal", pattern="^(public|internal|confidential|restricted)$")
    payload: dict[str, Any]


class DecisionCreate(BaseModel):
    decision_id: str | None = Field(default=None, max_length=96)
    owner: str = Field(min_length=1, max_length=255)
    status: str = Field(default="approved_for_bounded_validation", max_length=64)
    payload: dict[str, Any]


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/v1/workspaces/{workspace_id}/me")
def workspace_me(access: WorkspaceAccess = Depends(get_workspace_access)) -> dict[str, str | None]:
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
    access: WorkspaceAccess = Depends(require_role("viewer")),
    db: Session = Depends(get_db),
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


@app.post("/v1/workspaces/{workspace_id}/evidence", status_code=status.HTTP_201_CREATED)
def create_evidence(
    body: EvidenceCreate,
    access: WorkspaceAccess = Depends(require_role("analyst")),
    db: Session = Depends(get_db),
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
    db.commit()
    return {"evidence_id": record.id}


@app.post("/v1/workspaces/{workspace_id}/decisions", status_code=status.HTTP_201_CREATED)
def create_decision(
    body: DecisionCreate,
    access: WorkspaceAccess = Depends(require_role("manager")),
    db: Session = Depends(get_db),
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
    db.commit()
    return {"decision_id": record.id}

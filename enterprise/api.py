from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event, verify_audit_chain
from enterprise.config import get_settings
from enterprise.connectors import (
    ConnectorError,
    store_connector_credential,
    validate_connector,
)
from enterprise.db import SessionLocal, get_db
from enterprise.jobs import enqueue_job
from enterprise.models import (
    AuditEvent,
    Connector,
    ConnectorRun,
    DecisionRecord,
    DeletionRequest,
    EvidenceRecord,
    JobRecord,
    RetentionPolicy,
)
from enterprise.observability import install_observability
from enterprise.quota import UsageLimitExceeded, enforce
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
install_observability(app, settings)
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


class ConnectorCredentialInput(BaseModel):
    username: str | None = Field(default=None, max_length=320)
    password: SecretStr | None = None
    bearer_token: SecretStr | None = None
    headers: dict[str, SecretStr] = Field(default_factory=dict)


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    connector_type: Literal["rest_https", "postgresql"]
    endpoint_host: str = Field(min_length=1, max_length=255)
    configuration: dict[str, Any]
    credential: ConnectorCredentialInput


class ConnectorRunCreate(BaseModel):
    operation: dict[str, Any]


class RetentionPolicyInput(BaseModel):
    record_type: Literal[
        "evidence",
        "strategy",
        "decision",
        "outcome",
        "connector_run",
    ]
    retention_days: int = Field(ge=1, le=3650)
    enabled: bool = True


class DeletionRequestInput(BaseModel):
    request_type: Literal[
        "evidence",
        "connector",
        "workspace_analytical_records",
    ]
    target_id: str | None = Field(default=None, max_length=96)
    reason: str = Field(min_length=8, max_length=500)


DbDep = Annotated[Session, Depends(get_db)]
AccessDep = Annotated[WorkspaceAccess, Depends(get_workspace_access)]
ViewerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("viewer"))]
AnalystAccessDep = Annotated[WorkspaceAccess, Depends(require_role("analyst"))]
ManagerAccessDep = Annotated[WorkspaceAccess, Depends(require_role("manager"))]
AdminAccessDep = Annotated[WorkspaceAccess, Depends(require_role("admin"))]


def _credential_dict(value: ConnectorCredentialInput) -> dict:
    secret: dict[str, Any] = {}
    if value.username:
        secret["username"] = value.username
    if value.password:
        secret["password"] = value.password.get_secret_value()
    if value.bearer_token:
        secret["bearer_token"] = value.bearer_token.get_secret_value()
    if value.headers:
        secret["headers"] = {
            key: item.get_secret_value()
            for key, item in value.headers.items()
        }
    return secret


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
                headers={
                    "Retry-After": str(exc.decision.retry_after_seconds),
                },
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
    _limit_write(access)
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
    _limit_write(access)
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


@app.get("/v1/workspaces/{workspace_id}/connectors")
def list_connectors(
    access: ViewerAccessDep,
    db: DbDep,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Connector)
        .where(
            Connector.tenant_id == access.tenant_id,
            Connector.workspace_id == access.workspace_id,
        )
        .order_by(Connector.name.asc())
    ).all()
    return [
        {
            "connector_id": row.id,
            "name": row.name,
            "connector_type": row.connector_type,
            "endpoint_host": row.endpoint_host,
            "configuration": row.configuration,
            "status": row.status,
            "has_active_credential": bool(row.active_credential_id),
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@app.post(
    "/v1/workspaces/{workspace_id}/connectors",
    status_code=status.HTTP_201_CREATED,
)
def create_connector(
    body: ConnectorCreate,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    try:
        validate_connector(
            body.connector_type,
            body.endpoint_host.lower(),
            body.configuration,
            settings,
        )
    except ConnectorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    connector = Connector(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name=body.name,
        connector_type=body.connector_type,
        endpoint_host=body.endpoint_host.lower(),
        configuration=body.configuration,
        status="active",
    )
    db.add(connector)
    db.flush()
    store_connector_credential(
        db,
        access,
        connector,
        _credential_dict(body.credential),
    )
    append_audit_event(
        db,
        access,
        event_type="connector_created",
        object_type="connector",
        object_id=connector.id,
        detail={
            "name": connector.name,
            "connector_type": connector.connector_type,
            "endpoint_host": connector.endpoint_host,
        },
    )
    db.commit()
    return {"connector_id": connector.id}


@app.post("/v1/workspaces/{workspace_id}/connectors/{connector_id}/rotate")
def rotate_connector_credential(
    connector_id: str,
    body: ConnectorCredentialInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str | int]:
    _limit_write(access)
    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == access.tenant_id,
            Connector.workspace_id == access.workspace_id,
        )
    )
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector was not found.")
    credential = store_connector_credential(
        db,
        access,
        connector,
        _credential_dict(body),
    )
    append_audit_event(
        db,
        access,
        event_type="connector_credential_rotated",
        object_type="connector",
        object_id=connector.id,
        detail={"credential_version": credential.credential_version},
    )
    db.commit()
    return {
        "connector_id": connector.id,
        "credential_version": credential.credential_version,
        "status": "rotated",
    }


@app.post(
    "/v1/workspaces/{workspace_id}/connectors/{connector_id}/runs",
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_connector_run(
    connector_id: str,
    body: ConnectorRunCreate,
    access: AnalystAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    _limit_job(access)
    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == access.tenant_id,
            Connector.workspace_id == access.workspace_id,
            Connector.status == "active",
        )
    )
    if connector is None:
        raise HTTPException(status_code=404, detail="Active connector was not found.")

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
        job_type="connector_run",
        payload={
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
        event_type="connector_run_queued",
        object_type="connector_run",
        object_id=run.id,
        detail={"connector_id": connector.id, "job_id": job.id},
    )
    db.commit()
    return {"run_id": run.id, "job_id": job.id}


@app.get("/v1/workspaces/{workspace_id}/jobs/{job_id}")
def get_job(
    job_id: str,
    access: ViewerAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    job = db.scalar(
        select(JobRecord).where(
            JobRecord.id == job_id,
            JobRecord.tenant_id == access.tenant_id,
            JobRecord.workspace_id == access.workspace_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job was not found.")
    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "error_code": job.error_code,
        "result": job.result,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@app.post("/v1/workspaces/{workspace_id}/retention-policies")
def upsert_retention_policy(
    body: RetentionPolicyInput,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, Any]:
    _limit_write(access)
    policy = db.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.tenant_id == access.tenant_id,
            RetentionPolicy.workspace_id == access.workspace_id,
            RetentionPolicy.record_type == body.record_type,
        )
    )
    if policy is None:
        policy = RetentionPolicy(
            tenant_id=access.tenant_id,
            workspace_id=access.workspace_id,
            created_by=access.user_id,
            record_type=body.record_type,
            retention_days=body.retention_days,
            enabled=body.enabled,
        )
        db.add(policy)
        db.flush()
    else:
        policy.retention_days = body.retention_days
        policy.enabled = body.enabled

    append_audit_event(
        db,
        access,
        event_type="retention_policy_updated",
        object_type="retention_policy",
        object_id=policy.id,
        detail={
            "record_type": policy.record_type,
            "retention_days": policy.retention_days,
            "enabled": policy.enabled,
        },
    )
    db.commit()
    return {
        "policy_id": policy.id,
        "record_type": policy.record_type,
        "retention_days": policy.retention_days,
        "enabled": policy.enabled,
    }


@app.post(
    "/v1/workspaces/{workspace_id}/retention-policies/{policy_id}/run",
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_retention_policy(
    policy_id: str,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    _limit_job(access)
    policy = db.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.tenant_id == access.tenant_id,
            RetentionPolicy.workspace_id == access.workspace_id,
            RetentionPolicy.enabled.is_(True),
        )
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="Active retention policy was not found.")
    job = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="retention_purge",
        payload={"policy_id": policy.id},
        settings=settings,
    )
    db.commit()
    return {"job_id": job.id}


@app.post(
    "/v1/workspaces/{workspace_id}/deletion-requests",
    status_code=status.HTTP_201_CREATED,
)
def create_deletion_request(
    body: DeletionRequestInput,
    access: ManagerAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    if body.request_type in {"evidence", "connector"} and not body.target_id:
        raise HTTPException(
            status_code=400,
            detail="This deletion request type requires a target_id.",
        )
    request = DeletionRequest(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        request_type=body.request_type,
        target_id=body.target_id,
        reason=body.reason,
        status="pending",
    )
    db.add(request)
    db.flush()
    append_audit_event(
        db,
        access,
        event_type="deletion_request_created",
        object_type="deletion_request",
        object_id=request.id,
        detail={
            "request_type": request.request_type,
            "target_id": request.target_id,
        },
    )
    db.commit()
    return {"deletion_request_id": request.id, "status": request.status}


@app.post(
    "/v1/workspaces/{workspace_id}/deletion-requests/{request_id}/approve",
    status_code=status.HTTP_202_ACCEPTED,
)
def approve_deletion_request(
    request_id: str,
    access: AdminAccessDep,
    db: DbDep,
) -> dict[str, str]:
    _limit_write(access)
    _limit_job(access)
    request = db.scalar(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.tenant_id == access.tenant_id,
            DeletionRequest.workspace_id == access.workspace_id,
            DeletionRequest.status == "pending",
        )
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Pending deletion request was not found.")

    request.status = "approved"
    request.approved_by = access.user_id
    request.approved_at = datetime.now(UTC)
    job = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="deletion_execute",
        payload={"deletion_request_id": request.id},
        settings=settings,
    )
    append_audit_event(
        db,
        access,
        event_type="deletion_request_approved",
        object_type="deletion_request",
        object_id=request.id,
        detail={"job_id": job.id},
    )
    db.commit()
    return {
        "deletion_request_id": request.id,
        "job_id": job.id,
        "status": request.status,
    }


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

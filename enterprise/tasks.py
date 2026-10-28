from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event
from enterprise.auth import Principal
from enterprise.connectors import ConnectorError, execute_connector
from enterprise.models import (
    Connector,
    ConnectorCredential,
    ConnectorRun,
    DecisionRecord,
    DeletionRequest,
    EvidenceRecord,
    JobRecord,
    OutcomeRecord,
    RetentionPolicy,
    StrategyRecord,
)
from enterprise.observability import CONNECTOR_RUNS
from enterprise.retention import purge_expired_records
from enterprise.tenancy import WorkspaceAccess


class TaskError(RuntimeError):
    pass


def _system_access(job: JobRecord) -> WorkspaceAccess:
    principal = Principal(
        subject="system:prism-worker",
        email=None,
        display_name="PRISM Worker",
        claims={"system": True},
    )
    return WorkspaceAccess(
        tenant_id=job.tenant_id,
        workspace_id=job.workspace_id,
        user_id=job.created_by,
        principal=principal,
        role="admin",
        data_clearance="restricted",
    )


def run_connector_job(db: Session, job: JobRecord) -> dict:
    connector_id = str(job.payload.get("connector_id", ""))
    run_id = str(job.payload.get("run_id", ""))
    operation = job.payload.get("operation")
    if not connector_id or not run_id or not isinstance(operation, dict):
        raise TaskError("Connector job payload is incomplete.")

    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == job.tenant_id,
            Connector.workspace_id == job.workspace_id,
            Connector.status == "active",
        )
    )
    run = db.scalar(
        select(ConnectorRun).where(
            ConnectorRun.id == run_id,
            ConnectorRun.tenant_id == job.tenant_id,
            ConnectorRun.workspace_id == job.workspace_id,
        )
    )
    if connector is None or run is None:
        raise TaskError("Connector or connector run was not found.")

    try:
        result = execute_connector(db, connector, operation)
    except ConnectorError:
        run.status = "failed"
        run.error_code = "connector_error"
        run.completed_at = datetime.now(UTC)
        CONNECTOR_RUNS.labels(
            connector_type=connector.connector_type,
            status="failed",
        ).inc()
        raise

    run.status = "succeeded"
    run.row_count = int(result["row_count"])
    run.content_hash = str(result["content_hash"])
    run.schema_summary = dict(result["schema_summary"])
    run.completed_at = datetime.now(UTC)

    evidence_id = f"EVD-CONN-{uuid.uuid4().hex.upper()}"
    db.add(
        EvidenceRecord(
            id=evidence_id,
            tenant_id=job.tenant_id,
            workspace_id=job.workspace_id,
            created_by=job.created_by,
            evidence_class="connector_run_metadata",
            classification="internal",
            payload={
                "connector_id": connector.id,
                "connector_type": connector.connector_type,
                "run_id": run.id,
                "row_count": run.row_count,
                "content_hash": run.content_hash,
                "schema_summary": run.schema_summary,
                "method": "bounded_read_only_connector_extract",
                "raw_rows_persisted": False,
            },
        )
    )
    append_audit_event(
        db,
        _system_access(job),
        event_type="connector_run_completed",
        object_type="connector_run",
        object_id=run.id,
        detail={
            "connector_id": connector.id,
            "row_count": run.row_count,
            "evidence_id": evidence_id,
        },
    )
    CONNECTOR_RUNS.labels(
        connector_type=connector.connector_type,
        status="succeeded",
    ).inc()
    return {
        "run_id": run.id,
        "evidence_id": evidence_id,
        "row_count": run.row_count,
        "content_hash": run.content_hash,
    }


def run_retention_job(db: Session, job: JobRecord) -> dict:
    policy_id = str(job.payload.get("policy_id", ""))
    policy = db.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.tenant_id == job.tenant_id,
            RetentionPolicy.workspace_id == job.workspace_id,
            RetentionPolicy.enabled.is_(True),
        )
    )
    if policy is None:
        raise TaskError("Active retention policy was not found.")

    deleted = purge_expired_records(
        db,
        tenant_id=job.tenant_id,
        workspace_id=job.workspace_id,
        record_type=policy.record_type,
        retention_days=policy.retention_days,
    )
    append_audit_event(
        db,
        _system_access(job),
        event_type="retention_purge_completed",
        object_type="retention_policy",
        object_id=policy.id,
        detail={
            "record_type": policy.record_type,
            "retention_days": policy.retention_days,
            "deleted_records": deleted,
        },
    )
    return {"policy_id": policy.id, "deleted_records": deleted}


def _delete_connector(db: Session, job: JobRecord, connector_id: str) -> dict:
    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == job.tenant_id,
            Connector.workspace_id == job.workspace_id,
        )
    )
    if connector is None:
        return {"connector_deleted": False}

    db.execute(
        delete(ConnectorCredential).where(
            ConnectorCredential.tenant_id == job.tenant_id,
            ConnectorCredential.workspace_id == job.workspace_id,
            ConnectorCredential.connector_id == connector_id,
        )
    )
    db.execute(
        delete(ConnectorRun).where(
            ConnectorRun.tenant_id == job.tenant_id,
            ConnectorRun.workspace_id == job.workspace_id,
            ConnectorRun.connector_id == connector_id,
        )
    )
    db.delete(connector)
    return {"connector_deleted": True}


def run_deletion_job(db: Session, job: JobRecord) -> dict:
    request_id = str(job.payload.get("deletion_request_id", ""))
    request = db.scalar(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.tenant_id == job.tenant_id,
            DeletionRequest.workspace_id == job.workspace_id,
        )
    )
    if request is None or request.status != "approved":
        raise TaskError("Deletion request is missing or is not approved.")

    result: dict[str, int | bool] = {}
    if request.request_type == "evidence":
        deleted = db.execute(
            delete(EvidenceRecord).where(
                EvidenceRecord.tenant_id == job.tenant_id,
                EvidenceRecord.workspace_id == job.workspace_id,
                EvidenceRecord.id == request.target_id,
            )
        )
        result["evidence_deleted"] = int(deleted.rowcount or 0)
    elif request.request_type == "connector" and request.target_id:
        result.update(_delete_connector(db, job, request.target_id))
    elif request.request_type == "workspace_analytical_records":
        for name, model in [
            ("evidence", EvidenceRecord),
            ("strategy", StrategyRecord),
            ("decision", DecisionRecord),
            ("outcome", OutcomeRecord),
            ("connector_runs", ConnectorRun),
        ]:
            deleted = db.execute(
                delete(model).where(
                    model.tenant_id == job.tenant_id,
                    model.workspace_id == job.workspace_id,
                )
            )
            result[name] = int(deleted.rowcount or 0)
    else:
        raise TaskError("Unsupported deletion request type.")

    request.status = "completed"
    request.completed_at = datetime.now(UTC)
    request.result = result
    append_audit_event(
        db,
        _system_access(job),
        event_type="deletion_request_completed",
        object_type="deletion_request",
        object_id=request.id,
        detail={
            "request_type": request.request_type,
            "target_id": request.target_id,
            "result": result,
        },
    )
    return {"deletion_request_id": request.id, **result}


def dispatch_job(db: Session, job: JobRecord) -> dict:
    if job.job_type == "connector_run":
        return run_connector_job(db, job)
    if job.job_type == "retention_purge":
        return run_retention_job(db, job)
    if job.job_type == "deletion_execute":
        return run_deletion_job(db, job)
    raise TaskError("Unsupported job type.")

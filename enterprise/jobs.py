from __future__ import annotations

import socket
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.models import JobRecord


def enqueue_job(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    created_by: str,
    job_type: str,
    payload: dict,
    settings: EnterpriseSettings | None = None,
    run_after: datetime | None = None,
) -> JobRecord:
    settings = settings or get_settings()
    record = JobRecord(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        created_by=created_by,
        job_type=job_type,
        payload=payload,
        status="queued",
        max_attempts=settings.job_max_attempts,
        run_after=run_after or datetime.now(UTC),
    )
    db.add(record)
    db.flush()
    return record


def claim_next_job(
    db: Session,
    worker_id: str,
    settings: EnterpriseSettings | None = None,
) -> JobRecord | None:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    statement = (
        select(JobRecord)
        .where(
            JobRecord.run_after <= now,
            JobRecord.attempts < JobRecord.max_attempts,
            or_(
                JobRecord.status == "queued",
                (
                    (JobRecord.status == "running")
                    & (JobRecord.lease_until.is_not(None))
                    & (JobRecord.lease_until < now)
                ),
            ),
        )
        .order_by(JobRecord.run_after.asc(), JobRecord.created_at.asc())
        .limit(1)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)

    record = db.scalar(statement)
    if record is None:
        return None

    record.status = "running"
    record.attempts += 1
    record.locked_by = worker_id
    record.lease_until = now + timedelta(seconds=settings.job_lease_seconds)
    record.started_at = record.started_at or now
    record.error_code = None
    db.flush()
    return record


def mark_job_succeeded(db: Session, record: JobRecord, result: dict) -> None:
    record.status = "succeeded"
    record.result = result
    record.completed_at = datetime.now(UTC)
    record.lease_until = None
    record.locked_by = None
    record.error_code = None
    db.flush()


def mark_job_failed(
    db: Session,
    record: JobRecord,
    error_code: str,
    settings: EnterpriseSettings | None = None,
) -> None:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    record.error_code = error_code[:80]
    record.lease_until = None
    record.locked_by = None
    if record.attempts >= record.max_attempts:
        record.status = "failed"
        record.completed_at = now
    else:
        record.status = "queued"
        delay = min(60, 2 ** record.attempts)
        record.run_after = now + timedelta(seconds=delay)
    db.flush()


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:12]}"

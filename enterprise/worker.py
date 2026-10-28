from __future__ import annotations

import logging
import time

from enterprise.config import get_settings
from enterprise.db import SessionLocal, set_tenant_context
from enterprise.jobs import (
    claim_next_job,
    default_worker_id,
    mark_job_failed,
    mark_job_succeeded,
)
from enterprise.observability import JOBS
from enterprise.tasks import dispatch_job

LOGGER = logging.getLogger("prism.enterprise.worker")


def run_once(worker_id: str | None = None) -> bool:
    settings = get_settings()
    worker_id = worker_id or default_worker_id()

    with SessionLocal() as db:
        job = claim_next_job(db, worker_id, settings)
        if job is None:
            db.rollback()
            return False
        db.commit()

        try:
            set_tenant_context(db, job.tenant_id, job.workspace_id)
            result = dispatch_job(db, job)
            mark_job_succeeded(db, job, result)
            db.commit()
            JOBS.labels(job_type=job.job_type, status="succeeded").inc()
            return True
        except Exception as exc:
            db.rollback()
            error_code = type(exc).__name__.lower()[:80]
            mark_job_failed(db, job, error_code, settings)
            db.commit()
            JOBS.labels(job_type=job.job_type, status="failed").inc()
            LOGGER.exception(
                "PRISM worker job failed: job_type=%s job_id=%s error_code=%s",
                job.job_type,
                job.id,
                error_code,
            )
            return True


def main() -> None:
    settings = get_settings()
    worker_id = default_worker_id()
    LOGGER.info("PRISM worker started: worker_id=%s", worker_id)
    while True:
        processed = run_once(worker_id)
        if not processed:
            time.sleep(settings.job_poll_seconds)


if __name__ == "__main__":
    main()

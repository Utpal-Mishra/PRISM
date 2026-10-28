from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from enterprise.models import (
    ConnectorRun,
    DecisionRecord,
    EvidenceRecord,
    OutcomeRecord,
    StrategyRecord,
)
from enterprise.p2_models import DataSnapshot

RETENTION_MODELS = {
    "evidence": EvidenceRecord,
    "strategy": StrategyRecord,
    "decision": DecisionRecord,
    "outcome": OutcomeRecord,
    "connector_run": ConnectorRun,
    "data_snapshot": DataSnapshot,
}


def purge_expired_records(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    record_type: str,
    retention_days: int,
    now: datetime | None = None,
) -> int:
    model = RETENTION_MODELS.get(record_type)
    if model is None:
        raise ValueError("Unsupported retention record type.")
    if retention_days < 1:
        raise ValueError("Retention period must be at least one day.")

    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    result = db.execute(
        delete(model).where(
            model.tenant_id == tenant_id,
            model.workspace_id == workspace_id,
            model.created_at < cutoff,
        )
    )
    return int(result.rowcount or 0)

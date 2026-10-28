from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from enterprise.models import (
    ConnectorRun,
    DecisionRecord,
    EvidenceRecord,
    OutcomeRecord,
    StrategyRecord,
)
from enterprise.p2_models import DataAsset, DataSnapshot

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

    if model is DataSnapshot:
        expired = db.scalars(
            select(DataSnapshot).where(
                DataSnapshot.tenant_id == tenant_id,
                DataSnapshot.workspace_id == workspace_id,
                DataSnapshot.created_at < cutoff,
            )
        ).all()
        if not expired:
            return 0

        asset_ids = {item.asset_id for item in expired}
        snapshot_ids = [item.id for item in expired]
        db.execute(
            delete(DataSnapshot).where(
                DataSnapshot.tenant_id == tenant_id,
                DataSnapshot.workspace_id == workspace_id,
                DataSnapshot.id.in_(snapshot_ids),
            )
        )
        for asset_id in asset_ids:
            asset = db.scalar(
                select(DataAsset).where(
                    DataAsset.id == asset_id,
                    DataAsset.tenant_id == tenant_id,
                    DataAsset.workspace_id == workspace_id,
                )
            )
            if asset is None:
                continue
            latest = db.scalar(
                select(DataSnapshot)
                .where(
                    DataSnapshot.tenant_id == tenant_id,
                    DataSnapshot.workspace_id == workspace_id,
                    DataSnapshot.asset_id == asset_id,
                )
                .order_by(DataSnapshot.version.desc())
                .limit(1)
            )
            asset.latest_snapshot_id = latest.id if latest is not None else None
        return len(expired)

    result = db.execute(
        delete(model).where(
            model.tenant_id == tenant_id,
            model.workspace_id == workspace_id,
            model.created_at < cutoff,
        )
    )
    return int(result.rowcount or 0)

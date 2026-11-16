from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.connectors import Connector, fetch_connector_rows
from enterprise.phase18_models import QueryCacheEntry


def _cache_id(
    tenant_id: str,
    workspace_id: str,
    connector_id: str,
    operation: dict,
) -> str:
    raw = json.dumps(
        {
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "connector_id": connector_id,
            "operation": operation,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_rows_with_cache(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    created_by: str,
    connector: Connector,
    operation: dict,
    classification: str,
    settings: EnterpriseSettings | None = None,
) -> tuple[list[dict], bool]:
    settings = settings or get_settings()
    cacheable = bool(operation.get("cacheable", True))
    cache_id = _cache_id(
        tenant_id,
        workspace_id,
        connector.id,
        operation,
    )
    now = datetime.now(UTC)

    if cacheable:
        cached = db.scalar(
            select(QueryCacheEntry).where(
                QueryCacheEntry.id == cache_id,
                QueryCacheEntry.tenant_id == tenant_id,
                QueryCacheEntry.workspace_id == workspace_id,
                QueryCacheEntry.expires_at > now,
            )
        )
        if cached is not None:
            rows = cached.result.get("rows", [])
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)], True

    rows = fetch_connector_rows(db, connector, operation, settings)
    if cacheable:
        expires_at = now + timedelta(seconds=settings.connector_cache_ttl_seconds)
        existing = db.get(QueryCacheEntry, cache_id)
        if existing is None:
            db.add(
                QueryCacheEntry(
                    id=cache_id,
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    created_by=created_by,
                    cache_scope=f"connector:{connector.id}",
                    cache_key=cache_id,
                    classification=classification,
                    result={"rows": rows},
                    expires_at=expires_at,
                )
            )
        else:
            existing.result = {"rows": rows}
            existing.classification = classification
            existing.expires_at = expires_at

        cached_rows = db.scalars(
            select(QueryCacheEntry)
            .where(
                QueryCacheEntry.tenant_id == tenant_id,
                QueryCacheEntry.workspace_id == workspace_id,
            )
            .order_by(QueryCacheEntry.created_at.desc())
        ).all()
        overflow = cached_rows[settings.workload_max_cached_entries :]
        if overflow:
            db.execute(
                delete(QueryCacheEntry).where(
                    QueryCacheEntry.id.in_([item.id for item in overflow])
                )
            )

    return rows, False


def purge_expired_cache(db: Session, now: datetime | None = None) -> int:
    result = db.execute(
        delete(QueryCacheEntry).where(
            QueryCacheEntry.expires_at <= (now or datetime.now(UTC))
        )
    )
    return int(result.rowcount or 0)

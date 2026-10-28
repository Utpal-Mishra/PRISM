from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from enterprise.models import UsageBucket
from enterprise.tenancy import WorkspaceAccess


@dataclass(frozen=True)
class UsageDecision:
    allowed: bool
    count: int
    limit: int
    retry_after_seconds: int


class UsageLimitExceeded(RuntimeError):
    def __init__(self, decision: UsageDecision) -> None:
        self.decision = decision
        super().__init__("Workspace usage limit exceeded.")


def _window_start(now: datetime, window_seconds: int) -> datetime:
    epoch = int(now.timestamp())
    start_epoch = epoch - (epoch % window_seconds)
    return datetime.fromtimestamp(start_epoch, tz=UTC)


def _bucket_id(
    tenant_id: str,
    workspace_id: str,
    action: str,
    start: datetime,
    window_seconds: int,
) -> str:
    raw = (
        f"{tenant_id}:{workspace_id}:{action}:"
        f"{int(start.timestamp())}:{window_seconds}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def consume(
    db: Session,
    access: WorkspaceAccess,
    *,
    action: str,
    limit: int,
    window_seconds: int,
    amount: int = 1,
) -> UsageDecision:
    now = datetime.now(UTC)
    start = _window_start(now, window_seconds)
    bucket_id = _bucket_id(
        access.tenant_id,
        access.workspace_id,
        action,
        start,
        window_seconds,
    )

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = (
            pg_insert(UsageBucket)
            .values(
                id=bucket_id,
                tenant_id=access.tenant_id,
                workspace_id=access.workspace_id,
                action=action,
                window_start=start,
                window_seconds=window_seconds,
                count=amount,
            )
            .on_conflict_do_update(
                index_elements=[UsageBucket.id],
                set_={"count": UsageBucket.count + amount},
            )
            .returning(UsageBucket.count)
        )
        count = int(db.scalar(statement) or amount)
    else:
        bucket = db.scalar(
            select(UsageBucket).where(UsageBucket.id == bucket_id)
        )
        if bucket is None:
            bucket = UsageBucket(
                id=bucket_id,
                tenant_id=access.tenant_id,
                workspace_id=access.workspace_id,
                action=action,
                window_start=start,
                window_seconds=window_seconds,
                count=amount,
            )
            db.add(bucket)
            count = amount
        else:
            bucket.count += amount
            count = bucket.count
        db.flush()

    elapsed = int((now - start).total_seconds())
    retry_after = max(1, window_seconds - elapsed)
    return UsageDecision(
        allowed=count <= limit,
        count=count,
        limit=limit,
        retry_after_seconds=retry_after,
    )


def enforce(
    db: Session,
    access: WorkspaceAccess,
    *,
    action: str,
    limit: int,
    window_seconds: int,
    amount: int = 1,
) -> UsageDecision:
    decision = consume(
        db,
        access,
        action=action,
        limit=limit,
        window_seconds=window_seconds,
        amount=amount,
    )
    if not decision.allowed:
        raise UsageLimitExceeded(decision)
    return decision

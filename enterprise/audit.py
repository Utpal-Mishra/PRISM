from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.models import AuditEvent
from enterprise.tenancy import WorkspaceAccess

GENESIS_HASH = "0" * 64


def _canonical_event(
    access: WorkspaceAccess,
    event_type: str,
    object_type: str,
    object_id: str | None,
    detail: dict,
    created_at: datetime,
) -> bytes:
    payload = {
        "tenant_id": access.tenant_id,
        "workspace_id": access.workspace_id,
        "actor_subject": access.principal.subject,
        "event_type": event_type,
        "object_type": object_type,
        "object_id": object_id,
        "detail": detail,
        "created_at": created_at.isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def append_audit_event(
    db: Session,
    access: WorkspaceAccess,
    event_type: str,
    object_type: str,
    object_id: str | None = None,
    detail: dict | None = None,
    settings: EnterpriseSettings | None = None,
) -> AuditEvent:
    settings = settings or get_settings()
    secret = settings.audit_hmac_key.get_secret_value().encode("utf-8")
    if len(secret) < 32:
        raise RuntimeError("Audit HMAC key is not configured strongly enough.")

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:scope))"),
            {"scope": f"{access.tenant_id}:{access.workspace_id}"},
        )

    previous = db.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == access.tenant_id,
            AuditEvent.workspace_id == access.workspace_id,
        )
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(1)
    )
    previous_hash = previous.event_hash if previous else GENESIS_HASH
    created_at = datetime.now(UTC)
    message = previous_hash.encode("ascii") + _canonical_event(
        access,
        event_type,
        object_type,
        object_id,
        detail or {},
        created_at,
    )
    event_hash = hmac.new(secret, message, hashlib.sha256).hexdigest()
    event = AuditEvent(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        actor_subject=access.principal.subject,
        event_type=event_type,
        object_type=object_type,
        object_id=object_id,
        detail=detail or {},
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )
    db.add(event)
    return event


def verify_audit_chain(
    events: list[AuditEvent],
    settings: EnterpriseSettings | None = None,
) -> bool:
    settings = settings or get_settings()
    secret = settings.audit_hmac_key.get_secret_value().encode("utf-8")
    previous_hash = GENESIS_HASH
    for event in sorted(events, key=lambda item: (item.created_at, item.id)):
        if event.previous_hash != previous_hash:
            return False
        payload = {
            "tenant_id": event.tenant_id,
            "workspace_id": event.workspace_id,
            "actor_subject": event.actor_subject,
            "event_type": event.event_type,
            "object_type": event.object_type,
            "object_id": event.object_id,
            "detail": event.detail,
            "created_at": event.created_at.isoformat(),
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        expected = hmac.new(
            secret,
            previous_hash.encode("ascii") + canonical,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, event.event_hash):
            return False
        previous_hash = event.event_hash
    return True

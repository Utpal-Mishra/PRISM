from __future__ import annotations

import hashlib
import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enterprise.phase18_models import ArtifactVersion
from enterprise.tenancy import WorkspaceAccess


def content_hash(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def append_artifact_version(
    db: Session,
    access: WorkspaceAccess,
    *,
    artifact_type: str,
    artifact_id: str,
    classification: str,
    payload: dict,
    change_note: str = "",
) -> ArtifactVersion:
    highest = db.scalar(
        select(func.max(ArtifactVersion.version)).where(
            ArtifactVersion.tenant_id == access.tenant_id,
            ArtifactVersion.workspace_id == access.workspace_id,
            ArtifactVersion.artifact_type == artifact_type,
            ArtifactVersion.artifact_id == artifact_id,
        )
    )
    record = ArtifactVersion(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        version=int(highest or 0) + 1,
        classification=classification,
        payload=payload,
        content_hash=content_hash(payload),
        change_note=change_note,
    )
    db.add(record)
    db.flush()
    return record

from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.models import EvidenceRecord
from enterprise.p2_models import DataAsset, DataSnapshot, EvidenceEdge


class MaterializationError(RuntimeError):
    pass


def _normalize_rows(rows: list[dict]) -> list[dict]:
    return json.loads(json.dumps(rows, default=str))


def _content_hash(rows: list[dict]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _schema_summary(rows: list[dict]) -> dict:
    columns: dict[str, str] = {}
    for row in rows[:100]:
        for key, value in row.items():
            value_type = type(value).__name__
            existing = columns.get(str(key))
            if existing is None:
                columns[str(key)] = value_type
            elif existing != value_type:
                columns[str(key)] = "mixed"
    return {
        "columns": columns,
        "sampled_rows": min(len(rows), 100),
    }


def add_evidence_edge(
    db: Session,
    *,
    tenant_id: str,
    workspace_id: str,
    created_by: str,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    relation: str,
    classification: str,
    metadata_json: dict | None = None,
) -> EvidenceEdge:
    existing = db.scalar(
        select(EvidenceEdge).where(
            EvidenceEdge.tenant_id == tenant_id,
            EvidenceEdge.workspace_id == workspace_id,
            EvidenceEdge.source_type == source_type,
            EvidenceEdge.source_id == source_id,
            EvidenceEdge.target_type == target_type,
            EvidenceEdge.target_id == target_id,
            EvidenceEdge.relation == relation,
        )
    )
    if existing is not None:
        return existing

    edge = EvidenceEdge(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        created_by=created_by,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relation=relation,
        classification=classification,
        metadata_json=metadata_json or {},
    )
    db.add(edge)
    db.flush()
    return edge


def create_snapshot(
    db: Session,
    *,
    asset: DataAsset,
    rows: list[dict],
    connector_run_id: str,
    created_by: str,
    connector_type: str,
    settings: EnterpriseSettings | None = None,
) -> tuple[DataSnapshot, EvidenceRecord]:
    settings = settings or get_settings()
    locked_asset = db.scalar(
        select(DataAsset)
        .where(
            DataAsset.id == asset.id,
            DataAsset.tenant_id == asset.tenant_id,
            DataAsset.workspace_id == asset.workspace_id,
            DataAsset.status == "active",
        )
        .with_for_update()
    )
    if locked_asset is None:
        raise MaterializationError("Data asset is unavailable for materialisation.")
    asset = locked_asset

    normalized = _normalize_rows(rows)
    if len(normalized) > settings.materialized_dataset_max_rows:
        raise MaterializationError(
            "Materialized dataset exceeds the configured row limit."
        )

    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(encoded) > settings.materialized_dataset_max_bytes:
        raise MaterializationError(
            "Materialized dataset exceeds the configured byte limit."
        )

    highest = db.scalar(
        select(func.max(DataSnapshot.version)).where(
            DataSnapshot.tenant_id == asset.tenant_id,
            DataSnapshot.workspace_id == asset.workspace_id,
            DataSnapshot.asset_id == asset.id,
        )
    )
    version = int(highest or 0) + 1
    snapshot_id = f"SNAP-{uuid.uuid4().hex.upper()}"
    snapshot = DataSnapshot(
        id=snapshot_id,
        tenant_id=asset.tenant_id,
        workspace_id=asset.workspace_id,
        created_by=created_by,
        asset_id=asset.id,
        version=version,
        classification=asset.classification,
        connector_run_id=connector_run_id,
        row_count=len(normalized),
        size_bytes=len(encoded),
        content_hash=_content_hash(normalized),
        schema_summary=_schema_summary(normalized),
        rows=normalized,
        provenance={
            "source_connector_id": asset.source_connector_id,
            "connector_type": connector_type,
            "connector_run_id": connector_run_id,
            "method": "governed_bounded_connector_materialization_v1",
            "immutable_snapshot": True,
        },
        immutable=True,
    )
    db.add(snapshot)
    db.flush()

    asset.latest_snapshot_id = snapshot.id

    evidence_id = f"EVD-DATA-{uuid.uuid4().hex.upper()}"
    evidence = EvidenceRecord(
        id=evidence_id,
        tenant_id=asset.tenant_id,
        workspace_id=asset.workspace_id,
        created_by=created_by,
        evidence_class="materialized_dataset_snapshot",
        classification=asset.classification,
        payload={
            "data_asset_id": asset.id,
            "snapshot_id": snapshot.id,
            "snapshot_version": snapshot.version,
            "source_connector_id": asset.source_connector_id,
            "connector_run_id": connector_run_id,
            "row_count": snapshot.row_count,
            "size_bytes": snapshot.size_bytes,
            "content_hash": snapshot.content_hash,
            "schema_summary": snapshot.schema_summary,
            "method": "governed_bounded_connector_materialization_v1",
            "raw_rows_in_evidence": False,
            "handling_note_recorded": bool(asset.handling_note),
            "causal_status": "not_applicable",
        },
    )
    db.add(evidence)
    db.flush()

    add_evidence_edge(
        db,
        tenant_id=asset.tenant_id,
        workspace_id=asset.workspace_id,
        created_by=created_by,
        source_type="connector",
        source_id=asset.source_connector_id,
        target_type="data_asset",
        target_id=asset.id,
        relation="source_for",
        classification=asset.classification,
    )
    add_evidence_edge(
        db,
        tenant_id=asset.tenant_id,
        workspace_id=asset.workspace_id,
        created_by=created_by,
        source_type="data_asset",
        source_id=asset.id,
        target_type="data_snapshot",
        target_id=snapshot.id,
        relation="versioned_as",
        classification=asset.classification,
        metadata_json={"version": snapshot.version},
    )
    add_evidence_edge(
        db,
        tenant_id=asset.tenant_id,
        workspace_id=asset.workspace_id,
        created_by=created_by,
        source_type="data_snapshot",
        source_id=snapshot.id,
        target_type="evidence",
        target_id=evidence.id,
        relation="supports",
        classification=asset.classification,
    )
    return snapshot, evidence

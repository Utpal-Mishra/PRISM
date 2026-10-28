from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from enterprise.db import Base
from enterprise.models import TenantScopedRecord, now_utc, uuid_str


class DataAsset(TenantScopedRecord, Base):
    __tablename__ = "data_assets"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    source_connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    latest_snapshot_id: Mapped[str | None] = mapped_column(String(96))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_data_asset_workspace_name",
        ),
    )


class DataSnapshot(TenantScopedRecord, Base):
    __tablename__ = "data_snapshots"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    connector_run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rows: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "version",
            name="uq_data_snapshot_asset_version",
        ),
        Index(
            "ix_data_snapshot_workspace_asset_created",
            "workspace_id",
            "asset_id",
            "created_at",
        ),
    )


class EvidenceEdge(TenantScopedRecord, Base):
    __tablename__ = "evidence_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relation: Mapped[str] = mapped_column(String(80), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index(
            "ix_evidence_edge_source",
            "tenant_id",
            "workspace_id",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_evidence_edge_target",
            "tenant_id",
            "workspace_id",
            "target_type",
            "target_id",
        ),
    )


class DecisionCase(TenantScopedRecord, Base):
    __tablename__ = "decision_cases"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    business_question: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    materiality: Mapped[str] = mapped_column(String(32), nullable=False, default="advisory")
    max_classification: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    approval_state: Mapped[str] = mapped_column(String(48), nullable=False, default="not_reviewed")
    participating_teams: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    synthesis: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    job_id: Mapped[str | None] = mapped_column(String(36), index=True)
    approved_by: Mapped[str | None] = mapped_column(String(36))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_rationale: Mapped[str | None] = mapped_column(String(1000))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )


class AITeamRun(TenantScopedRecord, Base):
    __tablename__ = "ai_team_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    decision_case_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    team: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    finding: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    method: Mapped[str] = mapped_column(String(100), nullable=False)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint(
            "decision_case_id",
            "team",
            name="uq_ai_team_run_case_team",
        ),
    )

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from enterprise.db import Base
from enterprise.models import TenantScopedRecord, now_utc, uuid_str


class ArtifactVersion(TenantScopedRecord, Base):
    __tablename__ = "artifact_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    change_note: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "artifact_type",
            "artifact_id",
            "version",
            name="uq_artifact_version",
        ),
    )


class DatasetRegistryRecord(TenantScopedRecord, Base):
    __tablename__ = "dataset_registry_records"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    steward: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    cadence: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    certification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
    )
    classification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="internal",
    )
    source_asset_id: Mapped[str | None] = mapped_column(String(96), index=True)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_dataset_registry_workspace_name",
        ),
    )


class MetricRegistryRecord(TenantScopedRecord, Base):
    __tablename__ = "metric_registry_records"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    certification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
    )
    classification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="internal",
    )
    dataset_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_metric_registry_workspace_name",
        ),
    )


class GovernanceRecord(TenantScopedRecord, Base):
    __tablename__ = "governance_records"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    control_area: Mapped[str] = mapped_column(String(100), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    classification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="internal",
    )
    status: Mapped[str] = mapped_column(String(48), nullable=False, default="open")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )


class QueryCacheEntry(TenantScopedRecord, Base):
    __tablename__ = "query_cache_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    cache_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_query_cache_workspace_expires",
            "workspace_id",
            "expires_at",
        ),
    )


class ProcessingActivity(TenantScopedRecord, Base):
    __tablename__ = "processing_activities"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    lawful_basis: Mapped[str] = mapped_column(String(120), nullable=False)
    data_categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    data_subjects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retention_days: Mapped[int | None] = mapped_column(Integer)
    residency_regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )


class DPIAAssessment(TenantScopedRecord, Base):
    __tablename__ = "dpia_assessments"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    processing_activity_id: Mapped[str] = mapped_column(
        String(96),
        nullable=False,
        index=True,
    )
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    necessity: Mapped[str] = mapped_column(Text, nullable=False)
    proportionality: Mapped[str] = mapped_column(Text, nullable=False)
    risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    mitigations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    residual_risk: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DPARecord(TenantScopedRecord, Base):
    __tablename__ = "dpa_records"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_date: Mapped[str] = mapped_column(String(32), nullable=False)
    expiry_date: Mapped[str | None] = mapped_column(String(32))
    transfer_mechanism: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    subprocessor_terms: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class DataResidencyPolicy(TenantScopedRecord, Base):
    __tablename__ = "data_residency_policies"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    allowed_regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    prohibited_regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    classification_ceiling: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="restricted",
    )
    cross_border_basis: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class IncidentRecord(TenantScopedRecord, Base):
    __tablename__ = "incident_records"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    contained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notification_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class LegalHold(TenantScopedRecord, Base):
    __tablename__ = "legal_holds"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(96), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModelRegistryRecord(TenantScopedRecord, Base):
    __tablename__ = "model_registry_records"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    provider_config_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_style: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint_path: Mapped[str] = mapped_column(String(255), nullable=False)
    risk_classification: Mapped[str] = mapped_column(String(64), nullable=False)
    intended_use: Mapped[str] = mapped_column(Text, nullable=False)
    human_oversight: Mapped[str] = mapped_column(Text, nullable=False)
    transparency_notice: Mapped[str] = mapped_column(Text, nullable=False)
    classification_ceiling: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "alias",
            name="uq_model_registry_workspace_alias",
        ),
    )


class ModelEvaluation(TenantScopedRecord, Base):
    __tablename__ = "model_evaluations"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    model_registry_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    evaluation_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    thresholds: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AICallAudit(TenantScopedRecord, Base):
    __tablename__ = "ai_call_audits"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    model_registry_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    decision_case_id: Mapped[str | None] = mapped_column(String(96), index=True)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    injection_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    output_status: Mapped[str] = mapped_column(String(48), nullable=False)
    token_usage: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EnterprisePilot(TenantScopedRecord, Base):
    __tablename__ = "enterprise_pilots"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    organisation_label: Mapped[str] = mapped_column(String(200), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[str] = mapped_column(String(32), nullable=False)
    end_date: Mapped[str] = mapped_column(String(32), nullable=False)
    user_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    data_domains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    allowed_classifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    success_criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    security_review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
    )
    uat_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_utc,
        onupdate=now_utc,
    )


class PilotMeasurement(TenantScopedRecord, Base):
    __tablename__ = "pilot_measurements"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    pilot_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(160), nullable=False)
    target: Mapped[float | None] = mapped_column(Float)
    actual: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    evidence_id: Mapped[str | None] = mapped_column(String(96), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class UATFinding(TenantScopedRecord, Base):
    __tablename__ = "uat_findings"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    pilot_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str] = mapped_column(String(100), nullable=False)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    owner: Mapped[str] = mapped_column(String(255), nullable=False)

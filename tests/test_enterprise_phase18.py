from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from enterprise.artifacts import append_artifact_version
from enterprise.auth import Principal
from enterprise.config import EnterpriseSettings
from enterprise.connectors import validate_connector
from enterprise.db import Base
from enterprise.phase18_models import (
    AICallAudit,
    DataResidencyPolicy,
    DatasetRegistryRecord,
    DPARecord,
    DPIAAssessment,
    EnterprisePilot,
    GovernanceRecord,
    MetricRegistryRecord,
    ModelEvaluation,
    ModelRegistryRecord,
    PilotMeasurement,
    ProcessingActivity,
    QueryCacheEntry,
    UATFinding,
)
from enterprise.tenancy import WorkspaceAccess


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _access() -> WorkspaceAccess:
    return WorkspaceAccess(
        tenant_id="tenant-phase18",
        workspace_id="workspace-phase18",
        user_id="user-phase18",
        principal=Principal(
            subject="phase18-subject",
            email="phase18@example.com",
            display_name="Phase 18 Test",
            claims={},
        ),
        role="admin",
        data_clearance="restricted",
    )


def test_artifact_versions_are_append_only_and_incrementing() -> None:
    db = _session()
    access = _access()
    first = append_artifact_version(
        db,
        access,
        artifact_type="strategy",
        artifact_id="STR-1",
        classification="internal",
        payload={"priority": "high"},
        change_note="initial",
    )
    second = append_artifact_version(
        db,
        access,
        artifact_type="strategy",
        artifact_id="STR-1",
        classification="internal",
        payload={"priority": "medium"},
        change_note="reviewed",
    )
    db.commit()

    assert first.version == 1
    assert second.version == 2
    assert first.content_hash != second.content_hash


def test_phase18_registry_and_governance_models_persist() -> None:
    db = _session()
    access = _access()
    dataset = DatasetRegistryRecord(
        id="DS-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name="Orders",
        owner="Owner",
        steward="Steward",
        definition="Governed enterprise order records.",
        cadence="daily",
        certification="certified",
        classification="internal",
        aliases=["sales_orders"],
        status="active",
        version=1,
    )
    metric = MetricRegistryRecord(
        id="MET-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name="Net Revenue",
        definition="Revenue after discounts.",
        formula="SUM(net_revenue)",
        owner="Finance",
        certification="certified",
        classification="internal",
        dataset_ids=[dataset.id],
        aliases=[],
        status="active",
        version=1,
    )
    governance = GovernanceRecord(
        id="GOV-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        control_area="Metric certification",
        owner="Governance",
        classification="internal",
        status="compliant",
        payload={"metric_id": metric.id},
        version=1,
    )
    db.add_all([dataset, metric, governance])
    db.commit()

    assert db.get(DatasetRegistryRecord, "DS-1").certification == "certified"
    assert db.get(MetricRegistryRecord, "MET-1").dataset_ids == ["DS-1"]
    assert db.get(GovernanceRecord, "GOV-1").status == "compliant"


def test_expanded_connector_catalog_validates_governed_cloud_endpoints() -> None:
    settings = EnterpriseSettings(
        connector_allowed_hosts=(
            "snowflake.example.com,dbc.example.com,"
            "blob.example.com,storage.example.com,s3.example.com"
        )
    )
    validate_connector(
        "snowflake_sql_api",
        "snowflake.example.com",
        {"base_url": "https://snowflake.example.com", "warehouse": "WH"},
        settings,
    )
    validate_connector(
        "databricks_sql",
        "dbc.example.com",
        {
            "base_url": "https://dbc.example.com",
            "warehouse_id": "warehouse-1",
        },
        settings,
    )
    validate_connector(
        "azure_blob_https",
        "blob.example.com",
        {
            "base_url": "https://blob.example.com",
            "object_format": "csv",
        },
        settings,
    )
    validate_connector(
        "gcs_https",
        "storage.example.com",
        {
            "base_url": "https://storage.example.com",
            "object_format": "json",
        },
        settings,
    )
    validate_connector(
        "s3_presigned_https",
        "s3.example.com",
        {"object_format": "csv"},
        settings,
    )


def test_privacy_compliance_records_share_tenant_boundary() -> None:
    db = _session()
    access = _access()
    activity = ProcessingActivity(
        id="ROPA-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name="Customer analytics",
        purpose="Measure product usage and reporting outcomes.",
        lawful_basis="legitimate_interests",
        data_categories=["usage"],
        data_subjects=["customers"],
        recipients=["analytics"],
        retention_days=365,
        residency_regions=["EU"],
        owner="Privacy",
        status="active",
    )
    dpia = DPIAAssessment(
        id="DPIA-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        processing_activity_id=activity.id,
        risk_level="high",
        necessity="Processing is necessary for the approved analytical purpose.",
        proportionality="Only governed and bounded records are processed.",
        risks=[{"risk": "re-identification"}],
        mitigations=[{"control": "classification and access control"}],
        residual_risk="medium",
        reviewer="DPO",
        status="approved",
        reviewed_at=datetime.now(UTC),
    )
    dpa = DPARecord(
        id="DPA-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        counterparty="Processor",
        role="processor",
        effective_date="2026-01-01",
        transfer_mechanism="EU",
        status="active",
    )
    residency = DataResidencyPolicy(
        id="RES-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name="EU only",
        allowed_regions=["EU"],
        prohibited_regions=["US"],
        classification_ceiling="restricted",
        status="active",
    )
    db.add_all([activity, dpia, dpa, residency])
    db.commit()

    assert db.get(DPIAAssessment, "DPIA-1").status == "approved"
    assert db.get(DPARecord, "DPA-1").status == "active"
    assert db.get(DataResidencyPolicy, "RES-1").allowed_regions == ["EU"]


def test_model_evaluation_and_ai_audit_records_persist() -> None:
    db = _session()
    access = _access()
    model = ModelRegistryRecord(
        id="MODEL-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        provider_config_id="provider-1",
        alias="governed-model",
        model_name="model-1",
        api_style="openai_compatible",
        endpoint_path="/v1/chat/completions",
        risk_classification="decision_support",
        intended_use="Evidence-grounded analytical synthesis.",
        human_oversight="Manager review is required.",
        transparency_notice="AI-generated synthesis; human review required.",
        classification_ceiling="internal",
        enabled=False,
        prompt_version="v1",
    )
    evaluation = ModelEvaluation(
        id="EVAL-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        model_registry_id=model.id,
        evaluation_name="groundedness",
        dataset_version="eval-v1",
        metrics={"groundedness": 0.99, "citation_precision": 1.0},
        thresholds={"groundedness": 0.95, "citation_precision": 1.0},
        passed=True,
        reviewer="AI Governance",
    )
    audit = AICallAudit(
        id="AIAUD-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        model_registry_id=model.id,
        prompt_hash="a" * 64,
        classification="internal",
        evidence_ids=["EVD-1"],
        redaction_count=1,
        injection_flag=False,
        output_status="accepted",
        token_usage={"total_tokens": 100},
        latency_ms=120,
        detail={"prompt_body_stored": False},
    )
    db.add_all([model, evaluation, audit])
    db.commit()

    assert db.get(ModelEvaluation, "EVAL-1").passed is True
    assert db.get(AICallAudit, "AIAUD-1").detail["prompt_body_stored"] is False


def test_pilot_records_capture_measurement_and_uat() -> None:
    db = _session()
    access = _access()
    pilot = EnterprisePilot(
        id="PILOT-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name="Controlled pilot",
        organisation_label="Pilot organisation",
        owner="Pilot Owner",
        start_date="2026-11-01",
        end_date="2026-12-15",
        user_limit=10,
        data_domains=["reporting"],
        allowed_classifications=["internal"],
        success_criteria={"reporting_time_reduction_pct": 30},
        status="active",
        security_review_status="passed",
        uat_status="passed",
    )
    measurement = PilotMeasurement(
        id="PM-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        pilot_id=pilot.id,
        metric="reporting_time_reduction_pct",
        target=30.0,
        actual=35.0,
        unit="percent",
    )
    finding = UATFinding(
        id="UAT-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        pilot_id=pilot.id,
        severity="low",
        area="navigation",
        finding="Minor wording improvement requested.",
        status="open",
        owner="Product",
    )
    db.add_all([pilot, measurement, finding])
    db.commit()

    assert db.get(EnterprisePilot, "PILOT-1").security_review_status == "passed"
    assert db.get(PilotMeasurement, "PM-1").actual == 35.0
    assert db.get(UATFinding, "UAT-1").severity == "low"


def test_query_cache_model_supports_expiry() -> None:
    db = _session()
    access = _access()
    entry = QueryCacheEntry(
        id="cache-1",
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        cache_scope="connector:test",
        cache_key="key",
        classification="internal",
        result={"rows": [{"value": 1}]},
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.add(entry)
    db.commit()
    assert db.get(QueryCacheEntry, "cache-1").result["rows"][0]["value"] == 1

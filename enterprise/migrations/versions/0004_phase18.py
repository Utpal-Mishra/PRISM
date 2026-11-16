"""Original enterprise Phase 2-8 completion schema."""

from alembic import op

from enterprise import models, p2_models, phase18_models  # noqa: F401
from enterprise.db import Base

revision = "0004_phase18"
down_revision = "0003_control_plane"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE data_assets "
            "ADD COLUMN IF NOT EXISTS processing_activity_id VARCHAR(96)"
        )
        op.execute(
            "ALTER TABLE data_assets "
            "ADD COLUMN IF NOT EXISTS residency_region VARCHAR(100)"
        )
        tenant_tables = [
            "artifact_versions",
            "dataset_registry_records",
            "metric_registry_records",
            "governance_records",
            "query_cache_entries",
            "processing_activities",
            "dpia_assessments",
            "dpa_records",
            "data_residency_policies",
            "incident_records",
            "legal_holds",
            "model_registry_records",
            "model_evaluations",
            "ai_call_audits",
            "enterprise_pilots",
            "pilot_measurements",
            "uat_findings",
        ]
        for table in tenant_tables:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"""
                CREATE POLICY {table}_tenant_workspace_policy ON {table}
                USING (
                    tenant_id = current_setting('app.tenant_id', true)
                    AND workspace_id = current_setting('app.workspace_id', true)
                )
                WITH CHECK (
                    tenant_id = current_setting('app.tenant_id', true)
                    AND workspace_id = current_setting('app.workspace_id', true)
                )
                """
            )


def downgrade() -> None:
    for table in [
        "uat_findings",
        "pilot_measurements",
        "enterprise_pilots",
        "ai_call_audits",
        "model_evaluations",
        "model_registry_records",
        "legal_holds",
        "incident_records",
        "data_residency_policies",
        "dpa_records",
        "dpia_assessments",
        "processing_activities",
        "query_cache_entries",
        "governance_records",
        "metric_registry_records",
        "dataset_registry_records",
        "artifact_versions",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

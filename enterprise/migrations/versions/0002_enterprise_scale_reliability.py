"""P1 connectors, jobs, quotas, retention and provider governance."""

from alembic import op

from enterprise import models  # noqa: F401
from enterprise.db import Base

revision = "0002_enterprise_scale_reliability"
down_revision = "0001_enterprise_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

    if bind.dialect.name == "postgresql":
        tenant_tables = [
            "connectors",
            "connector_credentials",
            "connector_runs",
            "retention_policies",
            "deletion_requests",
            "ai_provider_configs",
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
        "ai_provider_configs",
        "deletion_requests",
        "retention_policies",
        "usage_buckets",
        "job_records",
        "connector_runs",
        "connector_credentials",
        "connectors",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

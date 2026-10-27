"""Enterprise identity, tenancy and persistence foundation."""

from alembic import op

from enterprise import models  # noqa: F401
from enterprise.db import Base

revision = "0001_enterprise_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    if bind.dialect.name == "postgresql":
        tenant_tables = [
            "evidence_records",
            "strategy_records",
            "decision_records",
            "outcome_records",
            "encrypted_secrets",
            "audit_events",
        ]
        for table in tenant_tables:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(
                f"""
                CREATE POLICY {table}_tenant_workspace_policy ON "{table}"
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
    Base.metadata.drop_all(bind=op.get_bind())

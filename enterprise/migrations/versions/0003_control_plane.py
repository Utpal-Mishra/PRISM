"""P2 governed data materialisation and AI Control Plane."""

from alembic import op

from enterprise import models  # noqa: F401
from enterprise import p2_models  # noqa: F401
from enterprise.db import Base

revision = "0003_control_plane"
down_revision = "0002_scale_reliability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)

    if bind.dialect.name == "postgresql":
        tenant_tables = [
            "data_assets",
            "data_snapshots",
            "evidence_edges",
            "decision_cases",
            "ai_team_runs",
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
        "ai_team_runs",
        "decision_cases",
        "evidence_edges",
        "data_snapshots",
        "data_assets",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

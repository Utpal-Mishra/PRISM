"""P2 governed data materialisation and AI Control Plane."""

from alembic import op

from enterprise import models, p2_models  # noqa: F401
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

        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_data_snapshot_update()
            RETURNS trigger AS $
            BEGIN
                RAISE EXCEPTION 'PRISM data snapshots are immutable';
            END;
            $ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER data_snapshots_immutable_update
            BEFORE UPDATE ON data_snapshots
            FOR EACH ROW EXECUTE FUNCTION reject_data_snapshot_update()
            """
        )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS reject_data_snapshot_update() CASCADE")
    for table in [
        "ai_team_runs",
        "decision_cases",
        "evidence_edges",
        "data_snapshots",
        "data_assets",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

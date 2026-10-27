from __future__ import annotations

import argparse

from sqlalchemy import select

from enterprise.db import SessionLocal
from enterprise.models import EnterpriseUser, Membership, Tenant, Workspace


def bootstrap(tenant_name: str, workspace_name: str, subject: str, email: str | None) -> None:
    with SessionLocal.begin() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.name == tenant_name))
        if tenant is None:
            tenant = Tenant(name=tenant_name)
            db.add(tenant)
            db.flush()

        workspace = db.scalar(
            select(Workspace).where(
                Workspace.tenant_id == tenant.id,
                Workspace.name == workspace_name,
            )
        )
        if workspace is None:
            workspace = Workspace(tenant_id=tenant.id, name=workspace_name)
            db.add(workspace)
            db.flush()

        user = db.scalar(select(EnterpriseUser).where(EnterpriseUser.external_subject == subject))
        if user is None:
            user = EnterpriseUser(external_subject=subject, email=email, display_name=email or subject)
            db.add(user)
            db.flush()

        membership = db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.workspace_id == workspace.id,
            )
        )
        if membership is None:
            db.add(
                Membership(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    role="admin",
                    data_clearance="restricted",
                )
            )

        print(f"tenant_id={tenant.id}")
        print(f"workspace_id={workspace.id}")
        print(f"admin_subject={subject}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the first PRISM enterprise tenant.")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--subject", required=True, help="OIDC subject (sub) claim")
    parser.add_argument("--email")
    args = parser.parse_args()
    bootstrap(args.tenant, args.workspace, args.subject, args.email)


if __name__ == "__main__":
    main()

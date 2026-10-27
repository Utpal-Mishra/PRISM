from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.auth import Principal, get_principal
from enterprise.db import get_db, set_tenant_context
from enterprise.models import EnterpriseUser, Membership, Workspace

ROLE_RANK = {"viewer": 10, "analyst": 20, "manager": 30, "admin": 40}
CLEARANCE_RANK = {"public": 10, "internal": 20, "confidential": 30, "restricted": 40}


@dataclass(frozen=True)
class WorkspaceAccess:
    tenant_id: str
    workspace_id: str
    user_id: str
    principal: Principal
    role: str
    data_clearance: str


def role_allows(actual: str, required: str) -> bool:
    return ROLE_RANK.get(actual.lower(), 0) >= ROLE_RANK.get(required.lower(), 10**9)


def clearance_allows(actual: str, required: str) -> bool:
    return CLEARANCE_RANK.get(actual.lower(), 0) >= CLEARANCE_RANK.get(
        required.lower(), 10**9
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]
DbDep = Annotated[Session, Depends(get_db)]


def get_workspace_access(
    workspace_id: str,
    principal: PrincipalDep,
    db: DbDep,
) -> WorkspaceAccess:
    row = db.execute(
        select(EnterpriseUser, Membership, Workspace)
        .join(Membership, Membership.user_id == EnterpriseUser.id)
        .join(Workspace, Workspace.id == Membership.workspace_id)
        .where(
            EnterpriseUser.external_subject == principal.subject,
            EnterpriseUser.active.is_(True),
            Membership.workspace_id == workspace_id,
            Membership.active.is_(True),
            Workspace.status == "active",
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active membership exists for this workspace.",
        )

    user, membership, workspace = row
    set_tenant_context(db, workspace.tenant_id, workspace.id)
    return WorkspaceAccess(
        tenant_id=workspace.tenant_id,
        workspace_id=workspace.id,
        user_id=user.id,
        principal=principal,
        role=membership.role.lower(),
        data_clearance=membership.data_clearance.lower(),
    )


WorkspaceAccessDep = Annotated[WorkspaceAccess, Depends(get_workspace_access)]


def require_role(required: str):
    def dependency(access: WorkspaceAccessDep) -> WorkspaceAccess:
        if not role_allows(access.role, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required} role or higher is required.",
            )
        return access

    return dependency


def require_clearance(required: str):
    def dependency(access: WorkspaceAccessDep) -> WorkspaceAccess:
        if not clearance_allows(access.data_clearance, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{required} data clearance or higher is required.",
            )
        return access

    return dependency

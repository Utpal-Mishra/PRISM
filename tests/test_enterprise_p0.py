import base64
import secrets

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event, verify_audit_chain
from enterprise.auth import Principal
from enterprise.config import EnterpriseSettings
from enterprise.crypto import EncryptedValue, FieldCipher
from enterprise.db import Base
from enterprise.models import AuditEvent, EnterpriseUser, Membership, Tenant, Workspace
from enterprise.tenancy import (
    WorkspaceAccess,
    clearance_allows,
    get_workspace_access,
    role_allows,
)


def test_role_and_clearance_hierarchy() -> None:
    assert role_allows("admin", "manager")
    assert role_allows("analyst", "viewer")
    assert not role_allows("viewer", "analyst")
    assert clearance_allows("restricted", "confidential")
    assert not clearance_allows("internal", "confidential")


def test_production_configuration_fails_closed() -> None:
    with pytest.raises(ValidationError):
        EnterpriseSettings(
            environment="production",
            database_url="sqlite+pysqlite:///unsafe.db",
            oidc_issuer="",
            oidc_audience="",
            audit_hmac_key="short",
            data_encryption_key_b64="",
        )


def test_field_cipher_round_trip() -> None:
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    settings = EnterpriseSettings(
        data_encryption_key_b64=key,
        data_encryption_key_version="test-v1",
    )
    cipher = FieldCipher(settings)
    encrypted = cipher.encrypt_json({"token": "secret-value"}, "connector:123")
    assert encrypted.key_version == "test-v1"
    assert "secret-value" not in encrypted.ciphertext
    assert cipher.decrypt_json(
        EncryptedValue(encrypted.key_version, encrypted.ciphertext),
        "connector:123",
    ) == {"token": "secret-value"}


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_workspace_membership_is_authoritative() -> None:
    db = _session()
    tenant = Tenant(name="Acme")
    db.add(tenant)
    db.flush()
    workspace = Workspace(tenant_id=tenant.id, name="Finance")
    user = EnterpriseUser(external_subject="oidc|alice", email="alice@example.com")
    db.add_all([workspace, user])
    db.flush()
    db.add(
        Membership(
            user_id=user.id,
            workspace_id=workspace.id,
            role="analyst",
            data_clearance="confidential",
        )
    )
    db.commit()

    principal = Principal(
        subject="oidc|alice",
        email="alice@example.com",
        display_name="Alice",
        claims={},
    )
    access = get_workspace_access(workspace.id, principal, db)
    assert access.tenant_id == tenant.id
    assert access.workspace_id == workspace.id
    assert access.role == "analyst"

    outsider = Principal(subject="oidc|mallory", email=None, display_name=None, claims={})
    with pytest.raises(HTTPException):
        get_workspace_access(workspace.id, outsider, db)


def test_audit_chain_detects_tampering() -> None:
    db = _session()
    settings = EnterpriseSettings(audit_hmac_key="a" * 48)
    principal = Principal(subject="oidc|alice", email=None, display_name=None, claims={})
    access = WorkspaceAccess(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        principal=principal,
        role="admin",
        data_clearance="restricted",
    )
    append_audit_event(db, access, "created", "evidence", "EVD-1", {"x": 1}, settings)
    db.commit()
    append_audit_event(db, access, "approved", "decision", "DEC-1", {"x": 2}, settings)
    db.commit()

    events = db.query(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id).all()
    assert verify_audit_chain(events, settings)

    events[0].detail = {"x": 999}
    assert not verify_audit_chain(events, settings)

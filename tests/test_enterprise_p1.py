import base64
import secrets
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from enterprise.ai_providers import (
    AIProviderPolicyError,
    rotate_provider_secret,
    validate_provider_policy,
)
from enterprise.auth import Principal
from enterprise.config import EnterpriseSettings
from enterprise.connectors import (
    ConnectorError,
    read_connector_secret,
    store_connector_credential,
    validate_connector,
)
from enterprise.crypto import FieldCipher
from enterprise.db import Base
from enterprise.jobs import (
    claim_next_job,
    enqueue_job,
    mark_job_failed,
    mark_job_succeeded,
)
from enterprise.models import (
    AIProviderConfig,
    Connector,
    ConnectorCredential,
    ConnectorRun,
    EvidenceRecord,
    JobRecord,
)
from enterprise.quota import UsageLimitExceeded, enforce
from enterprise.retention import purge_expired_records
from enterprise.tasks import record_task_failure
from enterprise.tenancy import WorkspaceAccess


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _access() -> WorkspaceAccess:
    principal = Principal(
        subject="oidc|p1-admin",
        email="admin@example.com",
        display_name="P1 Admin",
        claims={},
    )
    return WorkspaceAccess(
        tenant_id="tenant-p1",
        workspace_id="workspace-p1",
        user_id="user-p1",
        principal=principal,
        role="admin",
        data_clearance="restricted",
    )


def _cipher() -> FieldCipher:
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    return FieldCipher(
        EnterpriseSettings(
            data_encryption_key_b64=key,
            data_encryption_key_version="test-v1",
        )
    )


def test_connector_allowlist_and_https_boundary() -> None:
    settings = EnterpriseSettings(
        connector_allowed_hosts="api.example.com,*.internal.example"
    )
    validate_connector(
        "rest_https",
        "api.example.com",
        {"base_url": "https://api.example.com/v1"},
        settings,
    )
    validate_connector(
        "postgresql",
        "warehouse.internal.example",
        {"database": "analytics", "port": 5432},
        settings,
    )

    with pytest.raises(ConnectorError):
        validate_connector(
            "rest_https",
            "api.example.com",
            {"base_url": "http://api.example.com/v1"},
            settings,
        )

    with pytest.raises(ConnectorError):
        validate_connector(
            "rest_https",
            "unapproved.example.com",
            {"base_url": "https://unapproved.example.com"},
            settings,
        )

    with pytest.raises(ConnectorError):
        validate_connector(
            "postgresql",
            "warehouse.internal.example",
            {
                "database": "analytics",
                "port": 5432,
                "".join(["pass", "word"]): "-".join(["plain", "fixture"]),
            },
            settings,
        )


def test_connector_credential_rotation_revokes_previous_ciphertext() -> None:
    db = _session()
    access = _access()
    cipher = _cipher()
    connector = Connector(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        name="Warehouse",
        connector_type="postgresql",
        endpoint_host="warehouse.example.com",
        configuration={"database": "analytics", "port": 5432},
    )
    db.add(connector)
    db.flush()

    credential_key = "".join(["pass", "word"])
    first_value = "-".join(["fixture", "one"])
    second_value = "-".join(["fixture", "two"])
    first = store_connector_credential(
        db,
        access,
        connector,
        {"username": "reader", credential_key: first_value},
        cipher,
    )
    first_id = first.id
    first_ciphertext = first.ciphertext
    second = store_connector_credential(
        db,
        access,
        connector,
        {"username": "reader", credential_key: second_value},
        cipher,
    )
    db.flush()

    prior = db.get(ConnectorCredential, first_id)
    assert prior is not None
    assert prior.status == "revoked"
    assert prior.revoked_at is not None
    assert connector.active_credential_id == second.id
    assert first_value not in first_ciphertext
    assert second_value not in second.ciphertext
    assert read_connector_secret(db, connector, cipher) == {
        "username": "reader",
        credential_key: second_value,
    }


def test_job_queue_claim_success_and_retry() -> None:
    db = _session()
    access = _access()
    settings = EnterpriseSettings(job_lease_seconds=30, job_max_attempts=2)
    first = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="retention_purge",
        payload={"policy_id": "POL-1"},
        settings=settings,
    )
    second = enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="connector_run",
        payload={"connector_id": "CON-1"},
        settings=settings,
        run_after=datetime.now(UTC) + timedelta(minutes=5),
    )
    db.commit()

    claimed = claim_next_job(db, "worker-a", settings)
    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status == "running"
    assert claimed.attempts == 1
    assert claimed.lease_until is not None

    mark_job_failed(db, claimed, "temporary_error", settings)
    db.commit()
    retried = db.get(JobRecord, first.id)
    assert retried is not None
    assert retried.status == "queued"
    assert retried.error_code == "temporary_error"

    retried.run_after = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    claimed_again = claim_next_job(db, "worker-b", settings)
    assert claimed_again is not None
    assert claimed_again.id == first.id
    assert claimed_again.attempts == 2
    mark_job_succeeded(db, claimed_again, {"ok": True})
    db.commit()

    finished = db.get(JobRecord, first.id)
    assert finished is not None
    assert finished.status == "succeeded"
    assert finished.result == {"ok": True}
    assert db.get(JobRecord, second.id).status == "queued"


def test_workspace_usage_quota_is_enforced() -> None:
    db = _session()
    access = _access()
    decision = enforce(
        db,
        access,
        action="jobs",
        limit=1,
        window_seconds=60,
    )
    assert decision.allowed
    assert decision.count == 1

    with pytest.raises(UsageLimitExceeded) as exc:
        enforce(
            db,
            access,
            action="jobs",
            limit=1,
            window_seconds=60,
        )
    assert exc.value.decision.count == 2
    assert exc.value.decision.retry_after_seconds >= 1


def test_retention_purge_is_tenant_and_workspace_scoped() -> None:
    db = _session()
    access = _access()
    now = datetime.now(UTC)
    db.add_all(
        [
            EvidenceRecord(
                id="EVD-OLD",
                tenant_id=access.tenant_id,
                workspace_id=access.workspace_id,
                created_by=access.user_id,
                evidence_class="test",
                classification="internal",
                payload={},
                created_at=now - timedelta(days=400),
            ),
            EvidenceRecord(
                id="EVD-NEW",
                tenant_id=access.tenant_id,
                workspace_id=access.workspace_id,
                created_by=access.user_id,
                evidence_class="test",
                classification="internal",
                payload={},
                created_at=now - timedelta(days=10),
            ),
            EvidenceRecord(
                id="EVD-OTHER",
                tenant_id="tenant-other",
                workspace_id="workspace-other",
                created_by="user-other",
                evidence_class="test",
                classification="internal",
                payload={},
                created_at=now - timedelta(days=400),
            ),
        ]
    )
    db.commit()

    deleted = purge_expired_records(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        record_type="evidence",
        retention_days=365,
        now=now,
    )
    db.commit()

    assert deleted == 1
    assert db.get(EvidenceRecord, "EVD-OLD") is None
    assert db.get(EvidenceRecord, "EVD-NEW") is not None
    assert db.get(EvidenceRecord, "EVD-OTHER") is not None


def test_ai_provider_requires_allowlist_and_recorded_data_policy() -> None:
    settings = EnterpriseSettings(ai_provider_allowed_hosts="ai.example.com")
    policy = {
        "allowed_data_classes": ["public", "internal"],
        "provider_retention_acknowledged": True,
        "purpose": "Evidence-grounded analytical assistance",
    }
    validate_provider_policy("ai.example.com", policy, settings)

    with pytest.raises(AIProviderPolicyError):
        validate_provider_policy("unapproved.example.com", policy, settings)

    invalid = dict(policy)
    invalid["provider_retention_acknowledged"] = False
    with pytest.raises(AIProviderPolicyError):
        validate_provider_policy("ai.example.com", invalid, settings)


def test_ai_provider_secret_rotation_replaces_old_secret() -> None:
    db = _session()
    access = _access()
    cipher = _cipher()
    provider = AIProviderConfig(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        provider="example-ai",
        model="model-1",
        endpoint_host="ai.example.com",
        data_policy={
            "allowed_data_classes": ["public"],
            "provider_retention_acknowledged": True,
            "purpose": "test",
        },
        enabled=False,
    )
    db.add(provider)
    db.flush()

    first_value = "-".join(["provider", "fixture", "one"])
    second_value = "-".join(["provider", "fixture", "two"])
    first = rotate_provider_secret(db, access, provider, first_value, cipher)
    first_id = first.id
    db.flush()
    second = rotate_provider_secret(db, access, provider, second_value, cipher)
    db.flush()

    assert provider.credential_id == second.id
    assert db.get(type(first), first_id) is None
    assert second_value not in second.ciphertext



def test_connector_run_failure_tracks_retry_and_terminal_status() -> None:
    db = _session()
    access = _access()
    settings = EnterpriseSettings(job_max_attempts=2)
    run = ConnectorRun(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        connector_id="connector-1",
        status="queued",
    )
    db.add(run)
    db.flush()
    enqueue_job(
        db,
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        job_type="connector_run",
        payload={
            "connector_id": "connector-1",
            "run_id": run.id,
            "operation": {},
        },
        settings=settings,
    )
    db.commit()

    claimed = claim_next_job(db, "worker-a", settings)
    assert claimed is not None
    mark_job_failed(db, claimed, "connector_error", settings)
    record_task_failure(db, claimed, "connector_error")
    db.commit()
    assert db.get(ConnectorRun, run.id).status == "retrying"

    claimed.run_after = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    claimed_again = claim_next_job(db, "worker-b", settings)
    assert claimed_again is not None
    mark_job_failed(db, claimed_again, "connector_error", settings)
    record_task_failure(db, claimed_again, "connector_error")
    db.commit()

    failed_run = db.get(ConnectorRun, run.id)
    assert failed_run.status == "failed"
    assert failed_run.error_code == "connector_error"
    assert failed_run.completed_at is not None

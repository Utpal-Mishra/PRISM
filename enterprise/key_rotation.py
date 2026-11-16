from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from enterprise.crypto import EncryptedValue, FieldCipher
from enterprise.models import ConnectorCredential, EncryptedSecret
from enterprise.tenancy import WorkspaceAccess


def rotate_workspace_ciphertext(
    db: Session,
    access: WorkspaceAccess,
    cipher: FieldCipher | None = None,
) -> dict[str, int]:
    cipher = cipher or FieldCipher()
    connector_count = 0
    secret_count = 0

    credentials = db.scalars(
        select(ConnectorCredential).where(
            ConnectorCredential.tenant_id == access.tenant_id,
            ConnectorCredential.workspace_id == access.workspace_id,
        )
    ).all()
    for credential in credentials:
        if credential.key_version == cipher.settings.data_encryption_key_version:
            continue
        aad = (
            f"connector:{credential.connector_id}:"
            f"credential:{credential.credential_version}"
        )
        value = cipher.decrypt_json(
            EncryptedValue(
                key_version=credential.key_version,
                ciphertext=credential.ciphertext,
            ),
            aad,
        )
        rotated = cipher.encrypt_json(value, aad)
        credential.ciphertext = rotated.ciphertext
        credential.key_version = rotated.key_version
        connector_count += 1

    secrets = db.scalars(
        select(EncryptedSecret).where(
            EncryptedSecret.tenant_id == access.tenant_id,
            EncryptedSecret.workspace_id == access.workspace_id,
        )
    ).all()
    for secret in secrets:
        if secret.key_version == cipher.settings.data_encryption_key_version:
            continue
        if not secret.purpose.startswith("ai-provider:"):
            continue
        provider_id = secret.purpose.split(":", 1)[1]
        aad = f"ai-provider:{provider_id}"
        value = cipher.decrypt_json(
            EncryptedValue(
                key_version=secret.key_version,
                ciphertext=secret.ciphertext,
            ),
            aad,
        )
        rotated = cipher.encrypt_json(value, aad)
        secret.ciphertext = rotated.ciphertext
        secret.key_version = rotated.key_version
        secret_count += 1

    db.flush()
    return {
        "connector_credentials_rotated": connector_count,
        "encrypted_secrets_rotated": secret_count,
    }

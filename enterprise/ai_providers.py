from __future__ import annotations

from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings, get_settings
from enterprise.crypto import FieldCipher
from enterprise.models import AIProviderConfig, EncryptedSecret
from enterprise.tenancy import WorkspaceAccess


class AIProviderPolicyError(RuntimeError):
    pass


def provider_host_allowed(
    host: str,
    settings: EnterpriseSettings | None = None,
) -> bool:
    settings = settings or get_settings()
    host = host.strip().lower()
    for allowed in settings.ai_provider_allowed_host_list:
        if allowed.startswith("*."):
            suffix = allowed[1:]
            if host.endswith(suffix) and host != suffix[1:]:
                return True
        elif host == allowed:
            return True
    return False


def validate_provider_policy(
    endpoint_host: str,
    data_policy: dict,
    settings: EnterpriseSettings | None = None,
) -> None:
    settings = settings or get_settings()
    if not provider_host_allowed(endpoint_host, settings):
        raise AIProviderPolicyError(
            "AI provider host is not present in the deployment allowlist."
        )

    allowed = data_policy.get("allowed_data_classes")
    if not isinstance(allowed, list) or not allowed:
        raise AIProviderPolicyError(
            "AI provider policy must declare allowed_data_classes."
        )
    valid = {"public", "internal", "confidential", "restricted"}
    if any(str(item) not in valid for item in allowed):
        raise AIProviderPolicyError("AI provider policy contains an invalid data class.")

    if data_policy.get("provider_retention_acknowledged") is not True:
        raise AIProviderPolicyError(
            "AI provider retention/training terms must be acknowledged before enablement."
        )
    if not str(data_policy.get("purpose", "")).strip():
        raise AIProviderPolicyError("AI provider policy must record an approved purpose.")


def rotate_provider_secret(
    db: Session,
    access: WorkspaceAccess,
    provider: AIProviderConfig,
    api_key: str,
    cipher: FieldCipher | None = None,
) -> EncryptedSecret:
    if not api_key:
        raise AIProviderPolicyError("AI provider API key cannot be empty.")
    cipher = cipher or FieldCipher()
    aad = f"ai-provider:{provider.id}"
    encrypted = cipher.encrypt_json({"api_key": api_key}, aad)
    secret = EncryptedSecret(
        tenant_id=access.tenant_id,
        workspace_id=access.workspace_id,
        created_by=access.user_id,
        purpose=f"ai-provider:{provider.id}",
        ciphertext=encrypted.ciphertext,
        key_version=encrypted.key_version,
    )
    db.add(secret)
    db.flush()

    previous_id = provider.credential_id
    provider.credential_id = secret.id
    if previous_id:
        previous = db.get(EncryptedSecret, previous_id)
        if (
            previous
            and previous.tenant_id == access.tenant_id
            and previous.workspace_id == access.workspace_id
        ):
            db.delete(previous)
    return secret

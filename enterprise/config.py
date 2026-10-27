from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnterpriseSettings(BaseSettings):
    environment: Literal["development", "test", "production"] = "development"
    service_name: str = "PRISM Enterprise API"
    service_version: str = "0.1.0-p0"
    database_url: str = "sqlite+pysqlite:///./prism_enterprise.db"

    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_algorithms: str = "RS256,ES256"
    allow_dev_auth: bool = False

    allowed_origins: str = ""
    trusted_hosts: str = "localhost,127.0.0.1"

    max_upload_bytes: int = 25 * 1024 * 1024
    max_upload_rows: int = 100_000
    max_upload_columns: int = 250
    max_cell_chars: int = 32_768

    audit_hmac_key: SecretStr = SecretStr("")
    data_encryption_key_b64: SecretStr = SecretStr("")
    data_encryption_key_version: str = "v1"

    model_config = SettingsConfigDict(
        env_prefix="PRISM_",
        env_file=".env.enterprise",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def algorithms(self) -> list[str]:
        return [value.strip() for value in self.oidc_algorithms.split(",") if value.strip()]

    @property
    def allowed_origin_list(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [value.strip() for value in self.trusted_hosts.split(",") if value.strip()]

    @model_validator(mode="after")
    def validate_production_boundary(self) -> EnterpriseSettings:
        if self.environment != "production":
            return self

        if self.allow_dev_auth:
            raise ValueError("PRISM_ALLOW_DEV_AUTH must be false in production.")
        if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("Production PRISM requires PostgreSQL.")
        if not self.oidc_issuer or not self.oidc_audience:
            raise ValueError("Production PRISM requires OIDC issuer and audience.")
        if not self.oidc_issuer.startswith("https://"):
            raise ValueError("Production PRISM requires an HTTPS OIDC issuer.")
        if self.oidc_jwks_url and not self.oidc_jwks_url.startswith("https://"):
            raise ValueError("Production PRISM requires an HTTPS OIDC JWKS URL.")
        if len(self.audit_hmac_key.get_secret_value()) < 32:
            raise ValueError(
                "Production PRISM requires an audit HMAC key of at least 32 characters."
            )

        encoded = self.data_encryption_key_b64.get_secret_value()
        try:
            decoded = base64.urlsafe_b64decode(encoded.encode("ascii"))
        except Exception as exc:
            raise ValueError(
                "PRISM_DATA_ENCRYPTION_KEY_B64 must be urlsafe-base64."
            ) from exc
        if len(decoded) != 32:
            raise ValueError("Production PRISM requires a 32-byte AES-256 key.")
        return self


@lru_cache
def get_settings() -> EnterpriseSettings:
    return EnterpriseSettings()

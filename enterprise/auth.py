from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from enterprise.config import EnterpriseSettings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    email: str | None
    display_name: str | None
    claims: dict[str, object]


def _require_https_url(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"{label} must be an absolute HTTPS URL.")
    if parsed.username or parsed.password:
        raise RuntimeError(f"{label} must not contain URL credentials.")
    return value


@lru_cache(maxsize=8)
def _discover_jwks_uri(issuer: str) -> str:
    issuer = _require_https_url(issuer, "OIDC issuer")
    discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    with urllib.request.urlopen(discovery_url, timeout=5) as response:  # nosec B310
        payload = json.loads(response.read().decode("utf-8"))
    jwks_uri = payload.get("jwks_uri")
    if not jwks_uri or not isinstance(jwks_uri, str):
        raise RuntimeError("OIDC provider discovery did not return jwks_uri.")
    return _require_https_url(jwks_uri, "OIDC JWKS URL")


def _verify_token(token: str, settings: EnterpriseSettings) -> Principal:
    jwks_url = settings.oidc_jwks_url or _discover_jwks_uri(settings.oidc_issuer)
    jwks_url = _require_https_url(jwks_url, "OIDC JWKS URL")
    signing_key = PyJWKClient(jwks_url, timeout=5).get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=settings.algorithms,
        audience=settings.oidc_audience,
        issuer=settings.oidc_issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
    return Principal(
        subject=str(claims["sub"]),
        email=str(claims["email"]) if claims.get("email") else None,
        display_name=str(claims["name"]) if claims.get("name") else None,
        claims=claims,
    )


CredentialsDep = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer),
]
SettingsDep = Annotated[EnterpriseSettings, Depends(get_settings)]
DevSubjectDep = Annotated[
    str | None,
    Header(alias="X-PRISM-Dev-Subject"),
]
DevEmailDep = Annotated[
    str | None,
    Header(alias="X-PRISM-Dev-Email"),
]


def get_principal(
    credentials: CredentialsDep = None,
    dev_subject: DevSubjectDep = None,
    dev_email: DevEmailDep = None,
    settings: SettingsDep = None,
) -> Principal:
    if settings is None:
        settings = get_settings()

    if credentials is not None:
        try:
            return _verify_token(credentials.credentials, settings)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or unverifiable enterprise identity token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    if settings.environment != "production" and settings.allow_dev_auth and dev_subject:
        return Principal(
            subject=dev_subject,
            email=dev_email,
            display_name=dev_email or dev_subject,
            claims={"development_identity": True},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Enterprise authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

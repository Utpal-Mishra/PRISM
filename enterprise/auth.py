from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from functools import lru_cache

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


@lru_cache(maxsize=8)
def _discover_jwks_uri(issuer: str) -> str:
    discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    with urllib.request.urlopen(discovery_url, timeout=5) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    jwks_uri = payload.get("jwks_uri")
    if not jwks_uri or not isinstance(jwks_uri, str):
        raise RuntimeError("OIDC provider discovery did not return jwks_uri.")
    return jwks_uri


def _verify_token(token: str, settings: EnterpriseSettings) -> Principal:
    jwks_url = settings.oidc_jwks_url or _discover_jwks_uri(settings.oidc_issuer)
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


def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    dev_subject: str | None = Header(default=None, alias="X-PRISM-Dev-Subject"),
    dev_email: str | None = Header(default=None, alias="X-PRISM-Dev-Email"),
    settings: EnterpriseSettings = Depends(get_settings),
) -> Principal:
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

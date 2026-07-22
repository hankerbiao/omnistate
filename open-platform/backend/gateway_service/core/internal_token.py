"""Internal JWT used when the gateway calls the DML backend."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..config import GatewaySettings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _sign_hs256(message: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_upstream_access_token(
    *,
    settings: GatewaySettings,
    subject: str,
    key_id: str,
    request_id: str,
    required_scope: str | None = None,
    scopes: list[str] | tuple[str, ...] | None = None,
) -> str:
    """Create a short-lived JWT trusted by the upstream DML backend."""
    if settings.upstream_auth_algorithm != "HS256":
        raise ValueError("Only HS256 upstream auth tokens are supported")
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=settings.upstream_auth_ttl_seconds)
    payload: dict[str, Any] = {
        "iss": settings.upstream_auth_issuer,
        "aud": settings.upstream_auth_audience,
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "token_use": "open_platform_gateway",
        "client_id": key_id,
        "key_id": key_id,
        "request_id": request_id,
    }
    if required_scope:
        payload["scope"] = required_scope
    if scopes:
        payload["scopes"] = list(scopes)

    header = {"alg": settings.upstream_auth_algorithm, "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_b64 = _sign_hs256(signing_input, settings.upstream_auth_secret)
    return f"{header_b64}.{payload_b64}.{signature_b64}"

"""Tests for gateway-to-upstream authentication behavior."""

from __future__ import annotations

import json

from starlette.datastructures import Headers

from gateway_service.config import GatewaySettings
from gateway_service.core.internal_token import create_upstream_access_token
from gateway_service.domain.models import ApiKey
from gateway_service.infrastructure.upstream import _forward_headers


def _payload_from_token(token: str) -> dict:
    _, payload_b64, _ = token.split(".")
    padding = "=" * (-len(payload_b64) % 4)
    import base64

    return json.loads(base64.urlsafe_b64decode(payload_b64 + padding))


def test_forward_headers_strip_external_credentials_and_identity_headers() -> None:
    headers = Headers(
        {
            "Authorization": "Bearer external-api-key",
            "X-Open-Platform-Key-Id": "forged-key",
            "X-Open-Platform-User-Id": "forged-user",
            "Host": "example.test",
            "Content-Type": "application/json",
        }
    )

    forwarded = _forward_headers(headers)

    assert "Authorization" not in forwarded
    assert "authorization" not in {name.lower() for name in forwarded}
    assert "x-open-platform-key-id" not in {name.lower() for name in forwarded}
    assert "x-open-platform-user-id" not in {name.lower() for name in forwarded}
    assert forwarded["content-type"] == "application/json"


def test_create_upstream_access_token_contains_trusted_gateway_claims() -> None:
    settings = GatewaySettings(
        upstream_auth_secret="unit-test-secret",
        upstream_auth_issuer="dml-open-platform-test",
        upstream_auth_audience="dml-backend-test",
        upstream_auth_ttl_seconds=60,
    )

    token = create_upstream_access_token(
        settings=settings,
        subject="user_admin",
        key_id="key_test",
        request_id="req_test",
        required_scope="execution:read",
        scopes=["execution:read", "reports:read"],
    )
    payload = _payload_from_token(token)

    assert payload["iss"] == "dml-open-platform-test"
    assert payload["aud"] == "dml-backend-test"
    assert payload["sub"] == "user_admin"
    assert payload["client_id"] == "key_test"
    assert payload["key_id"] == "key_test"
    assert payload["request_id"] == "req_test"
    assert payload["token_use"] == "open_platform_gateway"
    assert payload["scope"] == "execution:read"
    assert payload["scopes"] == ["execution:read", "reports:read"]
    assert 0 < payload["exp"] - payload["iat"] <= 60


def test_api_key_can_carry_distinct_upstream_user_subject() -> None:
    key = ApiKey(
        id="key_test",
        name="demo",
        prefix="dml_test_",
        masked="dml_test_demo",
        status="active",
        scopes=["execution_tasks:read"],
        createdAt="2026-07-20T00:00:00+00:00",
        env="test",
        plaintext="dml_test_demo",
        ownerUserId="user_developer",
        upstreamUserId="dev",
    )

    assert key.ownerUserId == "user_developer"
    assert key.upstreamUserId == "dev"


def test_gateway_settings_rejects_empty_upstream_auth_secret(monkeypatch) -> None:
    monkeypatch.setenv("DML_GATEWAY_UPSTREAM_AUTH_SECRET", "   ")

    try:
        GatewaySettings.from_env()
    except ValueError as exc:
        assert "DML_GATEWAY_UPSTREAM_AUTH_SECRET" in str(exc)
    else:
        raise AssertionError("expected empty upstream auth secret to be rejected")

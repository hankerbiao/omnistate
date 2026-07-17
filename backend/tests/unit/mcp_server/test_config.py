"""MCP 配置测试。"""

from __future__ import annotations

import pytest

from app.mcp_server.config import MCPSettings


_ENV_KEYS = (
    "DML_MCP_BACKEND_URL",
    "DML_MCP_BACKEND_TOKEN",
    "DML_MCP_REQUEST_TIMEOUT",
    "DML_MCP_TRANSPORT",
    "DML_MCP_HOST",
    "DML_MCP_PORT",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_mcp_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)

    settings = MCPSettings.from_env()

    assert settings.backend_base_url == "http://127.0.0.1:8801"
    assert settings.transport == "stdio"
    assert settings.port == 8810


def test_mcp_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("DML_MCP_BACKEND_URL", "http://backend:9000/")
    monkeypatch.setenv("DML_MCP_BACKEND_TOKEN", "token-value")
    monkeypatch.setenv("DML_MCP_REQUEST_TIMEOUT", "8.5")
    monkeypatch.setenv("DML_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("DML_MCP_HOST", "localhost")
    monkeypatch.setenv("DML_MCP_PORT", "8899")

    settings = MCPSettings.from_env()

    assert settings.backend_base_url == "http://backend:9000"
    assert settings.backend_token == "token-value"
    assert settings.request_timeout_seconds == 8.5
    assert settings.transport == "streamable-http"
    assert settings.host == "localhost"
    assert settings.port == 8899


def test_mcp_settings_reject_invalid_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("DML_MCP_TRANSPORT", "sse")

    with pytest.raises(ValueError, match="DML_MCP_TRANSPORT"):
        MCPSettings.from_env()


def test_mcp_settings_reject_public_http_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("DML_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("DML_MCP_HOST", "0.0.0.0")

    with pytest.raises(ValueError, match="loopback hosts only"):
        MCPSettings.from_env()

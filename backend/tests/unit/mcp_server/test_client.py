"""DML 后端 MCP 客户端测试。"""

from __future__ import annotations

import httpx
import pytest

from app.mcp_server.client import BackendAPIError, DMLBackendClient
from app.mcp_server.config import MCPSettings


def _client(token: str = "test-token") -> DMLBackendClient:
    return DMLBackendClient(
        MCPSettings(
            backend_base_url="http://backend.test",
            backend_token=token,
        )
    )


@pytest.mark.asyncio
async def test_list_my_test_tasks_unwraps_api_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_request: httpx.Request | None = None

    async def fake_get(client_self, url, *, params=None):
        nonlocal captured_request
        captured_request = client_self.build_request("GET", url, params=params)
        return httpx.Response(
            200,
            request=captured_request,
            json={"code": 0, "message": "ok", "data": [{"task_id": "ET-1"}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await _client().list_my_test_tasks(limit=5)

    assert result == [{"task_id": "ET-1"}]
    assert captured_request is not None
    assert captured_request.url.params["limit"] == "5"
    assert captured_request.headers["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_backend_client_maps_unauthorized_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(client_self, url, *, params=None):
        request = client_self.build_request("GET", url, params=params)
        return httpx.Response(401, request=request, json={"detail": "not authenticated"})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(BackendAPIError, match="DML_MCP_BACKEND_TOKEN"):
        await _client(token="").list_my_test_tasks()

"""Tests for the DML Open Platform MCP service."""

from __future__ import annotations

import json
from typing import Any

import pytest

from gateway_service.config import GatewaySettings
from gateway_service.core.load_balancer import RoundRobinLoadBalancer
from gateway_service.domain.models import ApiKey, CallLog, UserQuota
from gateway_service.infrastructure.upstream import UpstreamResult
from mcp_server.compat import CompatibleFastMCP, _normalize_http_body, _normalize_tool_arguments
from mcp_server.tools import MCPToolError, MCPToolService


def _key(*, token: str = "dml_test_demo_local", scopes: list[str] | None = None) -> ApiKey:
    return ApiKey(
        id="key_test",
        name="MCP test key",
        prefix="dml_test_",
        masked="dml_test_demo",
        status="active",
        scopes=scopes or ["execution_tasks:read"],
        createdAt="2026-07-20T00:00:00+00:00",
        env="test",
        plaintext=token,
        ownerUserId="user_developer",
        upstreamUserId="dev",
        quota=UserQuota(),
    )


class FakeRepository:
    def __init__(self, key: ApiKey | None = None) -> None:
        self.key = key or _key()
        self.logs: list[CallLog] = []
        self.used: list[str] = []

    def find_key_by_plaintext(self, token: str) -> ApiKey | None:
        return self.key if self.key.plaintext == token else None

    def add_log(self, log: CallLog) -> None:
        self.logs.append(log)

    def mark_key_used(self, key_id: str) -> None:
        self.used.append(key_id)

    def close(self) -> None:
        pass


class FakeUpstreamClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def close(self) -> None:
        pass

    async def forward(self, **kwargs: Any) -> UpstreamResult:
        self.calls.append(kwargs)
        path = kwargs["upstream_path"]
        if path.endswith("/status"):
            return _json_result(
                {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "task_id": "ET-1",
                        "overall_status": "FAILED",
                        "case_count": 2,
                        "passed_case_count": 1,
                        "failed_case_count": 1,
                        "cases": [
                            {"case_id": "TC-1", "status": "PASSED"},
                            {"case_id": "TC-2", "status": "FAILED", "failure_message": "timeout"},
                        ],
                    },
                }
            )
        if path.endswith("/timeline"):
            return _json_result({"code": 0, "message": "ok", "data": {"events": []}})
        if path == "/api/v1/test-cases":
            return _json_result(
                {
                    "code": 0,
                    "message": "ok",
                    "data": [
                        {
                            "case_id": "TC-1",
                            "title": "login succeeds",
                            "status": "active",
                            "project_id": "PROJ-1",
                        }
                    ],
                }
            )
        return _json_result({"code": 0, "message": "ok", "data": [{"task_id": "ET-1"}]})


class FakeContainer:
    def __init__(self, *, repository: FakeRepository, upstream_client: FakeUpstreamClient) -> None:
        self.repository = repository
        self.upstream_client = upstream_client
        self.settings = GatewaySettings(upstream_auth_secret="unit-test-secret")
        self.load_balancer = RoundRobinLoadBalancer(("http://dml.test",))


def _service(
    *,
    key: ApiKey | None = None,
    upstream_client: FakeUpstreamClient | None = None,
    default_api_key: str = "dml_test_demo_local",
) -> tuple[MCPToolService, FakeRepository, FakeUpstreamClient]:
    repository = FakeRepository(key)
    upstream = upstream_client or FakeUpstreamClient()
    return (
        MCPToolService(
            container=FakeContainer(repository=repository, upstream_client=upstream),  # type: ignore[arg-type]
            default_api_key=default_api_key,
        ),
        repository,
        upstream,
    )


def _json_result(payload: dict[str, Any], status_code: int = 200) -> UpstreamResult:
    return UpstreamResult(
        status_code=status_code,
        headers={"content-type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
        latency_ms=1,
    )


def test_empty_list_tool_arguments_are_treated_as_empty_object() -> None:
    assert _normalize_tool_arguments([]) == {}
    assert _normalize_tool_arguments(None) == {}
    assert _normalize_tool_arguments({"limit": 5}) == {"limit": 5}


def test_http_tool_call_arguments_are_normalized_before_protocol_validation() -> None:
    body = (
        b'{"jsonrpc":"2.0","id":2,"method":"tools/call",'
        b'"params":{"name":"list_my_test_tasks","arguments":[]}}'
    )

    normalized = _normalize_http_body(body)

    assert b'"arguments":{}' in normalized


@pytest.mark.asyncio
async def test_compatible_fastmcp_accepts_empty_list_arguments() -> None:
    app = CompatibleFastMCP("unit-test")

    @app.tool()
    def no_arg_tool() -> dict[str, str]:
        return {"status": "ok"}

    result = await app.call_tool("no_arg_tool", [])

    content, structured = result
    assert content[0].text == '{\n  "status": "ok"\n}'
    assert structured == {"status": "ok"}


def test_list_my_open_capabilities_is_scoped_to_api_key() -> None:
    service, _, _ = _service()

    result = service.list_my_open_capabilities()

    assert [item["id"] for item in result["capabilities"]] == [
        "cap_list_tasks",
        "cap_task_status",
        "cap_task_timeline",
        "cap_task_biz_logs",
        "cap_report",
    ]
    task_status = next(item for item in result["capabilities"] if item["id"] == "cap_task_status")
    assert task_status["params"][0]["name"] == "task_id"
    assert task_status["params"][0]["type"] == "string"


def test_list_my_open_capabilities_includes_test_cases_for_authorized_key() -> None:
    service, _, _ = _service(key=_key(scopes=["execution_tasks:read", "test_cases:read"]))

    result = service.list_my_open_capabilities()

    capability_ids = [item["id"] for item in result["capabilities"]]
    assert "cap_list_specs" in capability_ids


def test_invalid_api_key_is_rejected() -> None:
    service, _, _ = _service(default_api_key="wrong-token")

    with pytest.raises(MCPToolError, match="Invalid or revoked API key"):
        service.list_my_open_capabilities()


@pytest.mark.asyncio
async def test_missing_scope_is_rejected() -> None:
    service, _, _ = _service(key=_key(scopes=["test_cases:read"]))

    with pytest.raises(MCPToolError, match="execution_tasks:read"):
        await service.list_my_test_tasks()


@pytest.mark.asyncio
async def test_list_test_cases_uses_capability_executor_and_records_usage() -> None:
    service, repository, upstream = _service(key=_key(scopes=["test_cases:read"]))

    result = await service.list_test_cases(project_id="PROJ-1", status="active", limit=5)

    assert result == {
        "testCases": [
            {
                "case_id": "TC-1",
                "title": "login succeeds",
                "status": "active",
                "project_id": "PROJ-1",
            }
        ],
        "total": 1,
    }
    assert upstream.calls[0]["upstream_path"] == "/api/v1/test-cases"
    assert dict(upstream.calls[0]["params"]) == {
        "limit": "5",
        "project_id": "PROJ-1",
        "status": "active",
    }
    assert repository.used == ["key_test"]
    assert repository.logs[0].endpoint == "/api/v1/open/test-specs/cases"


@pytest.mark.asyncio
async def test_list_tasks_uses_capability_executor_and_records_usage() -> None:
    service, repository, upstream = _service()

    result = await service.list_my_test_tasks(limit=5)

    assert result == {"tasks": [{"task_id": "ET-1"}], "total": 1}
    assert upstream.calls[0]["upstream_path"] == "/api/v1/execution/tasks/my"
    assert dict(upstream.calls[0]["params"]) == {"limit": "5"}
    assert repository.used == ["key_test"]
    assert repository.logs[0].endpoint == "/api/v1/open/execution/tasks/my"


@pytest.mark.asyncio
async def test_execution_report_reuses_aggregate_handler() -> None:
    service, repository, upstream = _service()

    result = await service.get_execution_report(task_id="ET-1", limit=25)

    assert [call["upstream_path"] for call in upstream.calls] == [
        "/api/v1/execution/tasks/ET-1/status",
        "/api/v1/execution/tasks/ET-1/timeline",
    ]
    assert result["task_id"] == "ET-1"
    assert result["pass_rate"] == 0.5
    assert repository.used == ["key_test"]

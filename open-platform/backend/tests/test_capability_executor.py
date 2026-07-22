"""Tests for Open Platform capability execution modes."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import Request

from gateway_service.config import GatewaySettings
from gateway_service.core.capability_executor import CapabilityExecutor
from gateway_service.core.catalog import CAPABILITY_BY_ID
from gateway_service.domain.enums import utc_now_iso
from gateway_service.domain.models import ApiKey, Capability, WebhookRecord
from gateway_service.infrastructure.upstream import UpstreamResult


def _api_key() -> ApiKey:
    return ApiKey(
        id="key_test",
        name="test key",
        prefix="dml_test_",
        masked="dml_test_demo",
        status="active",
        scopes=[
            "execution_tasks:read",
            "execution_tasks:write",
            "test_cases:read",
            "requirements:read",
            "projects:read",
        ],
        createdAt="2026-07-20T00:00:00+00:00",
        env="test",
        plaintext="dml_test_demo",
        ownerUserId="user_developer",
        upstreamUserId="dev",
    )


def _request(method: str, path: str, *, query: bytes = b"", body: bytes = b"") -> Request:
    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"authorization", b"Bearer external")],
            "query_string": query,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        },
        receive,
    )


class FakeUpstreamClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def forward(self, **kwargs: Any) -> UpstreamResult:
        self.calls.append(kwargs)
        path = kwargs["upstream_path"]
        if path.endswith("/status"):
            return _json_upstream(
                {
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "task_id": "ET-1",
                        "overall_status": "FAILED",
                        "case_count": 3,
                        "passed_case_count": 1,
                        "failed_case_count": 2,
                        "cases": [
                            {"case_id": "TC-1", "status": "PASSED"},
                            {"case_id": "TC-2", "status": "FAILED", "failure_message": "timeout"},
                            {"case_id": "TC-3", "status": "FAILED", "failure_message": "timeout"},
                        ],
                    },
                }
            )
        if path.endswith("/timeline"):
            return _json_upstream({"code": 0, "message": "ok", "data": {"events": []}})
        return _json_upstream({"code": 0, "message": "ok", "data": []})


class FakeRepository:
    def __init__(self) -> None:
        self.webhooks: list[WebhookRecord] = []

    def create_webhook(
        self,
        *,
        owner_user_id: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookRecord:
        record = WebhookRecord(
            id="wh_test",
            ownerUserId=owner_user_id,
            url=url,
            events=events,
            status="active",
            createdAt=utc_now_iso(),
        )
        self.webhooks.append(record)
        return record


def _executor(upstream_client: FakeUpstreamClient | None = None) -> CapabilityExecutor:
    return CapabilityExecutor(
        upstream_client=upstream_client or FakeUpstreamClient(),  # type: ignore[arg-type]
        repository=FakeRepository(),  # type: ignore[arg-type]
        settings=GatewaySettings(upstream_auth_secret="unit-test-secret"),
    )


def _json_upstream(payload: dict[str, Any], status_code: int = 200) -> UpstreamResult:
    return UpstreamResult(
        status_code=status_code,
        headers={"content-type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
        latency_ms=1,
    )


@pytest.mark.asyncio
async def test_list_specs_capability_targets_dml_test_cases_route() -> None:
    upstream = FakeUpstreamClient()
    executor = _executor(upstream)

    await executor.execute(
        capability=CAPABILITY_BY_ID["cap_list_specs"],
        path_params={},
        upstream_base_url="http://dml.test",
        request=_request("GET", "/api/v1/open/test-specs/cases", query=b"status=active"),
        body=b"",
        request_id="req_test",
        key=_api_key(),
    )

    assert upstream.calls[0]["upstream_path"] == "/api/v1/test-cases"
    assert dict(upstream.calls[0]["params"]) == {"status": "active"}


@pytest.mark.asyncio
async def test_new_proxy_capabilities_target_expected_dml_routes() -> None:
    upstream = FakeUpstreamClient()
    executor = _executor(upstream)
    key = _api_key()

    cases = [
        ("cap_dispatch_task", {}, "/api/v1/execution/tasks/dispatch"),
        ("cap_rerun_task", {"task_id": "ET-1"}, "/api/v1/execution/tasks/ET-1/rerun"),
        ("cap_task_biz_logs", {"task_id": "ET-1"}, "/api/v1/execution/tasks/ET-1/biz-logs"),
        ("cap_get_case", {"case_id": "TC-1"}, "/api/v1/test-cases/TC-1"),
        ("cap_case_change_logs", {"case_id": "TC-1"}, "/api/v1/test-cases/TC-1/change-logs"),
        ("cap_list_requirements", {}, "/api/v1/requirements"),
        ("cap_get_requirement", {"req_id": "REQ-1"}, "/api/v1/requirements/REQ-1"),
        ("cap_list_projects", {}, "/api/v1/projects"),
        ("cap_get_project", {"project_id": "PROJ-1"}, "/api/v1/projects/PROJ-1"),
        ("cap_project_stats", {"project_id": "PROJ-1"}, "/api/v1/projects/PROJ-1/stats"),
        ("cap_project_blockers", {"project_id": "PROJ-1"}, "/api/v1/projects/PROJ-1/blockers"),
        ("cap_project_activities", {"project_id": "PROJ-1"}, "/api/v1/projects/PROJ-1/activities"),
    ]

    for capability_id, path_params, expected_upstream_path in cases:
        capability = CAPABILITY_BY_ID[capability_id]
        await executor.execute(
            capability=capability,
            path_params=path_params,
            upstream_base_url="http://dml.test",
            request=_request(capability.method.value, capability.path),
            body=b"{}" if capability.method.value == "POST" else b"",
            request_id=f"req_{capability_id}",
            key=key,
        )

    assert [call["upstream_path"] for call in upstream.calls] == [
        expected_upstream_path for _, _, expected_upstream_path in cases
    ]


@pytest.mark.asyncio
async def test_report_capability_aggregates_status_and_timeline() -> None:
    upstream = FakeUpstreamClient()
    executor = _executor(upstream)

    result = await executor.execute(
        capability=CAPABILITY_BY_ID["cap_report"],
        path_params={"task_id": "ET-1"},
        upstream_base_url="http://dml.test",
        request=_request("GET", "/api/v1/open/reports/ET-1"),
        body=b"",
        request_id="req_test",
        key=_api_key(),
    )

    assert [call["upstream_path"] for call in upstream.calls] == [
        "/api/v1/execution/tasks/ET-1/status",
        "/api/v1/execution/tasks/ET-1/timeline",
    ]
    payload = json.loads(result.body)
    assert payload["data"]["task_id"] == "ET-1"
    assert payload["data"]["pass_rate"] == 0.3333
    assert payload["data"]["top_failures"] == [{"reason": "timeout", "count": 2}]


@pytest.mark.asyncio
async def test_webhook_capability_is_served_locally() -> None:
    repository = FakeRepository()
    executor = CapabilityExecutor(
        upstream_client=FakeUpstreamClient(),  # type: ignore[arg-type]
        repository=repository,  # type: ignore[arg-type]
        settings=GatewaySettings(upstream_auth_secret="unit-test-secret"),
    )

    result = await executor.execute(
        capability=CAPABILITY_BY_ID["cap_webhook"],
        path_params={},
        upstream_base_url=None,
        request=_request("POST", "/api/v1/open/webhooks"),
        body=json.dumps({"url": "https://example.com/hook", "events": ["task.completed"]}).encode("utf-8"),
        request_id="req_test",
        key=_api_key(),
    )

    payload = json.loads(result.body)
    assert result.status_code == 201
    assert payload["data"]["webhook_id"] == "wh_test"
    assert repository.webhooks[0].ownerUserId == "user_developer"


def test_proxy_capability_requires_explicit_upstream_path() -> None:
    try:
        Capability(
            id="cap_bad_proxy",
            name="bad",
            category="test",
            method="GET",
            path="/api/v1/open/bad",
            summary="bad",
            description="bad",
            params=[],
            scope="bad:read",
            handler="proxy",
            sampleResponse="{}",
        )
    except ValueError as exc:
        assert "upstreamPath" in str(exc)
    else:
        raise AssertionError("proxy capability without upstreamPath should be rejected")

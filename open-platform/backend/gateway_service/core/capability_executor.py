"""Capability execution dispatcher for Open Platform APIs."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from fastapi import Request, status
from pydantic import ValidationError

from ..config import GatewaySettings
from ..domain.errors import GatewayError
from ..domain.models import APIResponse, ApiKey, Capability, WebhookRegistration
from ..infrastructure.repository import Repository
from ..infrastructure.upstream import UpstreamClient, UpstreamResult
from .internal_token import create_upstream_access_token
from .matching import resolve_upstream_path


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    capability: Capability
    path_params: dict[str, str]
    upstream_base_url: str | None
    request: Request
    body: bytes
    query_params: Mapping[str, Any] | None
    request_id: str
    key: ApiKey


class CapabilityHandler(Protocol):
    needs_upstream: bool

    async def execute(self, ctx: CapabilityRequest) -> UpstreamResult: ...


class CapabilityExecutor:
    """Route a matched capability to its implementation."""

    def __init__(
        self,
        *,
        upstream_client: UpstreamClient,
        repository: Repository,
        settings: GatewaySettings,
    ) -> None:
        upstream = CapabilityUpstream(upstream_client=upstream_client, settings=settings)
        self._handlers_by_id: dict[str, CapabilityHandler] = {
            "cap_webhook": WebhookRegistrationHandler(repository),
            "cap_report": ExecutionReportHandler(upstream),
        }
        self._proxy_handler = ProxyCapabilityHandler(upstream)

    def needs_upstream(self, capability: Capability) -> bool:
        return self._handler_for(capability).needs_upstream

    async def execute(
        self,
        *,
        capability: Capability,
        path_params: dict[str, str],
        upstream_base_url: str | None,
        request: Request,
        body: bytes,
        request_id: str,
        key: ApiKey,
        query_params: Mapping[str, Any] | None = None,
    ) -> UpstreamResult:
        handler = self._handler_for(capability)
        if handler.needs_upstream and not upstream_base_url:
            raise GatewayError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "UPSTREAM_REQUIRED",
                "Upstream service is required for this capability",
                "该开放能力需要调用 DML 后端，但当前没有可用上游。",
            )
        return await handler.execute(
            CapabilityRequest(
                capability=capability,
                path_params=path_params,
                upstream_base_url=upstream_base_url,
                request=request,
                body=body,
                query_params=query_params,
                request_id=request_id,
                key=key,
            )
        )

    def _handler_for(self, capability: Capability) -> CapabilityHandler:
        if capability.handler == "proxy":
            return self._proxy_handler
        handler = self._handlers_by_id.get(capability.id)
        if handler:
            return handler
        raise GatewayError(
            status.HTTP_501_NOT_IMPLEMENTED,
            "CAPABILITY_NOT_IMPLEMENTED",
            "Open Platform capability is not implemented",
            f"开放能力 {capability.id} 没有注册处理器。",
        )


class CapabilityUpstream:
    """Shared DML upstream caller used by proxy and aggregate handlers."""

    def __init__(self, *, upstream_client: UpstreamClient, settings: GatewaySettings) -> None:
        self._upstream_client = upstream_client
        self._settings = settings

    async def forward(
        self,
        ctx: CapabilityRequest,
        *,
        upstream_path: str,
        body: bytes | None = None,
        method: str | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> UpstreamResult:
        request_params = params
        if request_params is None:
            request_params = ctx.query_params if ctx.query_params is not None else ctx.request.query_params
        return await self._upstream_client.forward(
            upstream_base_url=ctx.upstream_base_url or "",
            upstream_path=upstream_path,
            request=ctx.request,
            body=ctx.body if body is None else body,
            request_id=ctx.request_id,
            key_id=ctx.key.id,
            owner_user_id=ctx.key.ownerUserId,
            upstream_authorization="Bearer " + self._create_token(ctx),
            method=method,
            params=request_params,
        )

    def _create_token(self, ctx: CapabilityRequest) -> str:
        return create_upstream_access_token(
            settings=self._settings,
            subject=ctx.key.upstreamUserId or ctx.key.ownerUserId,
            key_id=ctx.key.id,
            request_id=ctx.request_id,
            required_scope=ctx.capability.scope,
            scopes=ctx.key.scopes,
        )


class ProxyCapabilityHandler:
    needs_upstream = True

    def __init__(self, upstream: CapabilityUpstream) -> None:
        self._upstream = upstream

    async def execute(self, ctx: CapabilityRequest) -> UpstreamResult:
        return await self._upstream.forward(
            ctx,
            upstream_path=resolve_upstream_path(ctx.capability, ctx.path_params),
        )


class WebhookRegistrationHandler:
    needs_upstream = False

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def execute(self, ctx: CapabilityRequest) -> UpstreamResult:
        registration = self._parse_registration(ctx.body)
        record = self._repository.create_webhook(
            owner_user_id=ctx.key.ownerUserId,
            url=str(registration.url),
            events=registration.events,
            secret=registration.secret,
        )
        return json_result(
            status_code=status.HTTP_201_CREATED,
            payload=APIResponse(
                data={
                    "webhook_id": record.id,
                    "status": record.status,
                    "events": record.events,
                    "created_at": record.createdAt,
                }
            ).model_dump(),
        )

    @staticmethod
    def _parse_registration(body: bytes) -> WebhookRegistration:
        try:
            payload = json.loads(body.decode("utf-8"))
            return WebhookRegistration.model_validate(payload)
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
            raise GatewayError(
                status.HTTP_400_BAD_REQUEST,
                "INVALID_WEBHOOK_REGISTRATION",
                "Invalid webhook registration payload",
                str(exc),
            ) from exc


class ExecutionReportHandler:
    needs_upstream = True

    def __init__(self, upstream: CapabilityUpstream) -> None:
        self._upstream = upstream

    async def execute(self, ctx: CapabilityRequest) -> UpstreamResult:
        task_id = ctx.path_params.get("task_id")
        if not task_id:
            raise GatewayError(
                status.HTTP_400_BAD_REQUEST,
                "MISSING_TASK_ID",
                "Missing task_id",
                "报告能力需要 task_id 路径参数。",
            )

        status_result = await self._upstream.forward(
            ctx,
            upstream_path=f"/api/v1/execution/tasks/{task_id}/status",
            body=b"",
            method="GET",
            params={},
        )
        if status_result.status_code >= 400:
            return status_result

        query_params = ctx.query_params or {}
        timeline_result = await self._upstream.forward(
            ctx,
            upstream_path=f"/api/v1/execution/tasks/{task_id}/timeline",
            body=b"",
            method="GET",
            params={"limit": query_params.get("limit", "200")},
        )
        if timeline_result.status_code >= 400:
            return timeline_result

        report = ExecutionReportMapper().map(
            task_id=task_id,
            status_data=read_enveloped_data(status_result),
            timeline_data=read_enveloped_data(timeline_result),
        )
        return json_result(status_code=status.HTTP_200_OK, payload=APIResponse(data=report).model_dump())


class ExecutionReportMapper:
    """Build the public execution report from DML execution responses."""

    def map(
        self,
        *,
        task_id: str,
        status_data: dict[str, Any],
        timeline_data: dict[str, Any],
    ) -> dict[str, Any]:
        cases = status_data.get("cases")
        if not isinstance(cases, list):
            raise GatewayError(
                status.HTTP_502_BAD_GATEWAY,
                "UPSTREAM_CONTRACT_ERROR",
                "Invalid execution status response",
                "DML 执行状态响应缺少 cases 数组。",
            )

        total = int(status_data.get("case_count") or len(cases))
        passed = int(status_data.get("passed_case_count") or 0)
        failed = int(status_data.get("failed_case_count") or 0)
        pass_rate = round(passed / total, 4) if total else None

        return {
            "task_id": task_id,
            "status": status_data.get("overall_status"),
            "pass_rate": pass_rate,
            "duration_ms": None,
            "total": total,
            "passed": passed,
            "failed": failed,
            "top_failures": self._top_failures(cases),
            "status_summary": status_data,
            "timeline": timeline_data,
        }

    @staticmethod
    def _top_failures(cases: list[Any]) -> list[dict[str, Any]]:
        reasons: Counter[str] = Counter()
        for item in cases:
            if not isinstance(item, dict) or item.get("status") != "FAILED":
                continue
            reason = str(item.get("failure_message") or "unknown")
            reasons[reason] += 1
        return [{"reason": reason, "count": count} for reason, count in reasons.most_common(5)]


def json_result(*, status_code: int, payload: dict[str, Any]) -> UpstreamResult:
    return UpstreamResult(
        status_code=status_code,
        headers={"content-type": "application/json"},
        body=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
        latency_ms=1,
    )


def read_enveloped_data(result: UpstreamResult) -> dict[str, Any]:
    try:
        payload = json.loads(result.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GatewayError(
            status.HTTP_502_BAD_GATEWAY,
            "UPSTREAM_CONTRACT_ERROR",
            "Invalid upstream JSON response",
            "DML 后端返回的不是合法 JSON。",
        ) from exc

    if not isinstance(payload, dict) or "data" not in payload:
        raise GatewayError(
            status.HTTP_502_BAD_GATEWAY,
            "UPSTREAM_CONTRACT_ERROR",
            "Invalid upstream response envelope",
            "DML 后端响应必须包含 data 字段。",
        )
    if not isinstance(payload["data"], dict):
        raise GatewayError(
            status.HTTP_502_BAD_GATEWAY,
            "UPSTREAM_CONTRACT_ERROR",
            "Invalid upstream response data",
            "DML 后端响应 data 必须是对象。",
        )
    return payload["data"]

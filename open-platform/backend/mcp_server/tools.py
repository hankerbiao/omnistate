"""MCP tool service backed by gateway_service capabilities."""

from __future__ import annotations

import json
import secrets
from typing import Any, Mapping

from fastapi import HTTPException

from gateway_service.common.container import GatewayContainer
from gateway_service.common.logging_utils import build_call_log, now_ms
from gateway_service.core.capability_executor import CapabilityExecutor
from gateway_service.core.catalog import CAPABILITIES, CAPABILITY_BY_ID
from gateway_service.domain.errors import GatewayError
from gateway_service.domain.models import ApiKey, Capability

from .adapter import build_mcp_request


MCP_TOOL_CAPABILITY_IDS = {
    "cap_list_tasks",
    "cap_task_status",
    "cap_task_timeline",
    "cap_list_specs",
    "cap_report",
}


class MCPToolError(RuntimeError):
    """Tool-level error surfaced to MCP clients."""


class MCPToolService:
    """Execute MCP tools by reusing Open Platform capability components."""

    def __init__(self, *, container: GatewayContainer, default_api_key: str = "") -> None:
        self._container = container
        self._default_api_key = default_api_key
        self._executor = CapabilityExecutor(
            upstream_client=container.upstream_client,
            repository=container.repository,
            settings=container.settings,
        )

    async def close(self) -> None:
        await self._container.upstream_client.close()
        self._container.repository.close()

    def list_my_open_capabilities(self, api_key: str | None = None) -> dict[str, Any]:
        key = self._authenticate(api_key)
        capabilities = [
            capability
            for capability in CAPABILITIES
            if capability.scope in key.scopes and not capability.scope.endswith(":write")
        ]
        return {
            "key": _key_summary(key),
            "capabilities": [capability.model_dump() for capability in capabilities],
        }

    async def list_my_test_tasks(self, *, limit: int = 20, api_key: str | None = None) -> dict[str, Any]:
        safe_limit = max(1, min(limit, 100))
        result = await self._execute_capability(
            "cap_list_tasks",
            api_key=api_key,
            path_params={},
            query_params={"limit": safe_limit},
        )
        if isinstance(result, list):
            return {"tasks": result, "total": len(result)}
        return result

    async def list_test_cases(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(limit, 100))
        query_params: dict[str, str | int] = {"limit": safe_limit}
        if project_id:
            query_params["project_id"] = project_id.strip()
        if status:
            query_params["status"] = status.strip()

        result = await self._execute_capability(
            "cap_list_specs",
            api_key=api_key,
            path_params={},
            query_params=query_params,
        )
        if isinstance(result, list):
            return {"testCases": result, "total": len(result)}
        return result

    async def get_test_task_status(self, *, task_id: str, api_key: str | None = None) -> dict[str, Any]:
        task_id = _require_non_empty(task_id, "task_id")
        return await self._execute_capability(
            "cap_task_status",
            api_key=api_key,
            path_params={"task_id": task_id},
        )

    async def get_test_task_timeline(
        self, *, task_id: str, limit: int = 100, api_key: str | None = None
    ) -> dict[str, Any]:
        task_id = _require_non_empty(task_id, "task_id")
        safe_limit = max(1, min(limit, 500))
        return await self._execute_capability(
            "cap_task_timeline",
            api_key=api_key,
            path_params={"task_id": task_id},
            query_params={"limit": safe_limit},
        )

    async def get_execution_report(
        self, *, task_id: str, limit: int = 200, api_key: str | None = None
    ) -> dict[str, Any]:
        task_id = _require_non_empty(task_id, "task_id")
        safe_limit = max(1, min(limit, 500))
        return await self._execute_capability(
            "cap_report",
            api_key=api_key,
            path_params={"task_id": task_id},
            query_params={"limit": safe_limit},
        )

    async def _execute_capability(
        self,
        capability_id: str,
        *,
        api_key: str | None,
        path_params: dict[str, str],
        query_params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        capability = CAPABILITY_BY_ID[capability_id]
        if capability.id not in MCP_TOOL_CAPABILITY_IDS:
            raise MCPToolError(f"Capability {capability.id} is not exposed as a read-only MCP tool")

        key = self._authenticate(api_key)
        self._require_scope(key, capability)
        normalized_query_params = _string_params(query_params)

        request_path = _resolve_public_path(capability, path_params)
        request = build_mcp_request(
            method=capability.method.value,
            path=request_path,
            api_key=api_key or self._default_api_key,
            query_params=normalized_query_params,
        )
        request_id = f"req_mcp_{secrets.token_hex(4)}"
        started_ms = now_ms()
        status_code = 500
        response_body: bytes | dict[str, Any] = {}
        error_code: str | None = None
        diagnosis: str | None = None

        try:
            upstream_base = (
                self._container.load_balancer.choose()
                if self._executor.needs_upstream(capability)
                else None
            )
            result = await self._executor.execute(
                capability=capability,
                path_params=path_params,
                upstream_base_url=upstream_base,
                request=request,  # type: ignore[arg-type]
                body=b"",
                query_params=normalized_query_params,
                request_id=request_id,
                key=key,
            )
            status_code = result.status_code
            response_body = result.body
            if result.status_code >= 400:
                raise MCPToolError(_response_text(result.body))
            return _response_payload(result.body)
        except HTTPException as exc:
            status_code = exc.status_code
            error_code = f"HTTP_{exc.status_code}"
            diagnosis = str(exc.detail)
            raise MCPToolError(str(exc.detail)) from exc
        except GatewayError as exc:
            status_code = exc.status_code
            error_code = exc.code
            diagnosis = exc.diagnosis
            raise MCPToolError(exc.message) from exc
        finally:
            self._container.repository.add_log(
                build_call_log(
                    request_id=request_id,
                    request=request,  # type: ignore[arg-type]
                    key=key,
                    status_code=status_code,
                    started_ms=started_ms,
                    gateway_latency_ms=max(1, round(now_ms() - started_ms)),
                    request_body=None,
                    response_body=response_body,
                    error_code=error_code,
                    diagnosis=diagnosis,
                )
            )
            if status_code < 400:
                self._container.repository.mark_key_used(key.id)

    def _authenticate(self, api_key: str | None) -> ApiKey:
        token = (api_key or self._default_api_key).strip()
        if not token:
            raise MCPToolError("Missing MCP API key. Set DML_MCP_API_KEY or pass an API key.")
        key = self._container.repository.find_key_by_plaintext(token)
        if not key or key.status != "active":
            raise MCPToolError("Invalid or revoked API key")
        return key

    @staticmethod
    def _require_scope(key: ApiKey, capability: Capability) -> None:
        if capability.scope not in key.scopes:
            raise MCPToolError(f"API key requires scope: {capability.scope}")


def _resolve_public_path(capability: Capability, path_params: dict[str, str]) -> str:
    path = capability.path
    for name, value in path_params.items():
        path = path.replace("{" + name + "}", value)
    return path


def _response_payload(body: bytes) -> dict[str, Any]:
    payload = json.loads(body.decode("utf-8"))
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _response_text(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")[:1000]


def _require_non_empty(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise MCPToolError(f"{field} is required")
    return normalized


def _key_summary(key: ApiKey) -> dict[str, Any]:
    return {
        "id": key.id,
        "name": key.name,
        "ownerUserId": key.ownerUserId,
        "scopes": key.scopes,
        "env": key.env,
    }


def _string_params(params: Mapping[str, str | int] | None) -> dict[str, str]:
    return {key: str(value) for key, value in (params or {}).items()}

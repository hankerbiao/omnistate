"""调试探针：把能力 + 用户输入解析为上游请求并执行探测。

把 ``api.console`` 路由里与调试请求构造、上游探测、错误体构造相关的逻辑
收敛到独立模块，使路由处理函数只负责校验与编排，便于单独测试与扩展。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx
from fastapi import Request

from ..config import GatewaySettings
from ..core.capability_executor import CapabilityExecutor
from ..domain.errors import GatewayError
from ..domain.models import ApiKey, Capability, DebugRequest, EnvName
from ..infrastructure.repository import Repository
from ..infrastructure.upstream import UpstreamClient


@dataclass(slots=True)
class ResolvedDebugRequest:
    """能力模板 + 用户输入解析后的可执行请求。"""

    upstream_path: str
    path_params: dict[str, str]
    query: dict[str, str]
    request_body: bytes
    request_url: str


def resolve_debug_request(
    capability: Capability, params: dict[str, str], env: EnvName
) -> ResolvedDebugRequest:
    """把能力路径模板与用户输入参数解析为可执行的上游请求。

    与网关运行时匹配逻辑一致：替换路径参数、收集 GET 查询参数、生成可点击的请求 URL。
    """
    resolved_path = capability.path
    path_params: dict[str, str] = {}
    for param in capability.params:
        value = params.get(param.name, "")
        if param.required and not value.strip():
            raise ValueError(f"Missing required param: {param.name}")
        if "{" + param.name + "}" in capability.path:
            path_params[param.name] = value
        resolved_path = resolved_path.replace("{" + param.name + "}", value)

    query = {
        name: value
        for name, value in params.items()
        if value and "{" + name + "}" not in capability.path and capability.method == "GET"
    }
    request_body = b"" if capability.method == "GET" else json.dumps(params).encode("utf-8")

    host = "open" if env == "live" else "sandbox"
    request_url = f"https://{host}.dml.example.com{resolved_path}"
    if query:
        query_string = "&".join(f"{name}={value}" for name, value in query.items())
        request_url = f"{request_url}?{query_string}"

    return ResolvedDebugRequest(
        upstream_path=resolved_path,
        path_params=path_params,
        query=query,
        request_body=request_body,
        request_url=request_url,
    )


def build_debug_error_body(status_code: int, message: str) -> str:
    """构造调试用的上游错误体（始终包裹在调试结果的 200 信封内）。"""
    return json.dumps({"code": status_code, "message": message}, ensure_ascii=False, indent=2)


async def run_debug_probe(
    *,
    capability: Capability,
    debug_request: DebugRequest,
    key: ApiKey,
    upstream_client: UpstreamClient,
    repository: Repository,
    upstream_base: str,
    request: Request,
    request_id: str,
    settings: GatewaySettings,
) -> dict[str, object]:
    """执行一次调试探测，返回与 API 约定一致的调试结果字典。"""
    resolved = resolve_debug_request(capability, debug_request.params, debug_request.env)
    started = time.perf_counter()
    executor = CapabilityExecutor(
        upstream_client=upstream_client,
        repository=repository,
        settings=settings,
    )
    try:
        upstream_base_url = upstream_base if executor.needs_upstream(capability) else None
        result = await executor.execute(
            capability=capability,
            path_params=resolved.path_params,
            upstream_base_url=upstream_base_url,
            request=request,
            body=resolved.request_body,
            query_params=resolved.query,
            request_id=request_id,
            key=key,
        )
        status_code = result.status_code
        response_body = result.body.decode("utf-8", errors="replace")
    except httpx.RequestError:
        status_code = 503
        response_body = build_debug_error_body(503, "无法连接上游服务，已返回调试错误")
    except GatewayError as exc:
        status_code = exc.status_code
        response_body = build_debug_error_body(exc.status_code, exc.message)

    return {
        "requestId": request_id,
        "statusCode": status_code,
        "latencyMs": max(1, round((time.perf_counter() - started) * 1000)),
        "requestUrl": resolved.request_url,
        "responseBody": response_body,
    }

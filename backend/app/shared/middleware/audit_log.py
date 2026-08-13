"""操作审计日志中间件（纯 ASGI 实现）。

记录所有写操作（POST/PUT/PATCH/DELETE）的完整审计信息：
- 操作者（actor_id / username / roles）
- 请求信息（method / path / body 脱敏后）
- 业务信息（resource_type / resource_id / action）
- 响应信息（status_code / duration_ms）

异步写入 MongoDB，不阻塞请求响应。

重要：本中间件必须实现为纯 ASGI 中间件，不能继承 Starlette 的
BaseHTTPMiddleware。原因：BaseHTTPMiddleware 的 call_next 会把下游路由（含认证
依赖注入）跑在一个独立的 asyncio 子任务里，导致认证依赖内 set_operation_context
设置的 contextvars 无法回传到中间件的任务上下文（经典 contextvars 隔离坑）。
纯 ASGI 中间件中下游与中间件运行在同一任务，contextvars 正常传播，中间件才能正确
读到操作者信息；否则 audit_logs 集合永远不会被创建（actor_id 恒为默认值 "-"）。
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.shared.context import get_operation_context, get_trace_context
from app.shared.core.logger import log
from app.shared.security.redaction import (
    redact_dict,
    redact_query_params,
    should_skip_body_logging,
)


# ── 配置 ────────────────────────────────────────────────────────────────

SKIP_PATHS = {
    "/health", "/health/ready", "/health/live",
    "/docs", "/openapi.json", "/redoc",
    "/favicon.ico",
}

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

MAX_BODY_SIZE = 4096  # 请求体记录最大字节数

# 路径前缀 → 资源类型映射
PATH_RESOURCE_MAP: dict[str, str] = {
    "/api/v1/requirements": "requirement",
    "/api/v1/test-cases": "test_case",
    "/api/v1/automation-test-cases": "automation_test_case",
    "/api/v1/work-items": "work_item",
    "/api/v1/auth/users": "user",
    "/api/v1/auth/roles": "role",
}

# 方法 → 默认操作类型
METHOD_ACTION_MAP: dict[str, str] = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

# 特殊路径后缀 → 操作类型覆盖
PATH_ACTION_OVERRIDES: dict[str, str] = {
    "/dispatch": "dispatch",
    "/assign": "assign",
    "/reassign": "reassign",
    "/rerun": "rerun",
    "/archive": "archive",
    "/cancel": "cancel",
    "/transition": "transition",
    "/login": "login",
}


class AuditLogMiddleware:
    """操作审计日志中间件（纯 ASGI 实现）。

    注册顺序：在 RequestLoggingMiddleware 之后（此时 TraceContext 已填充）；
    由于是纯 ASGI，下游路由与中间件同任务运行，OperationContext 在路由依赖注入
    阶段填充后，中间件在 await self.app(...) 之后可直接读到。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path

        # 跳过非审计路径
        if path in SKIP_PATHS or request.method not in AUDITED_METHODS:
            await self.app(scope, receive, send)
            return

        # 读取请求体（需在路由前读，因为 body 是流式的）
        body_bytes = await request.body()

        # 重新注入 body 供路由读取
        if body_bytes:
            saved_body = body_bytes

            async def _receive() -> Message:
                return {"type": "http.request", "body": saved_body, "more_body": False}
        else:
            _receive = receive

        start_time = time.monotonic()

        # 捕获响应状态码（纯 ASGI 中需从 send 消息里取）
        response_status: dict[str, int] = {}

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_status["status"] = message["status"]
            await send(message)

        # 纯 ASGI：下游与中间件同任务运行，contextvars（含操作者上下文）可传播
        await self.app(scope, _receive, _send)

        duration_ms = int((time.monotonic() - start_time) * 1000)
        status_code = response_status.get("status", 0)

        # 异步写入审计日志（此时操作者上下文已就绪）
        asyncio.create_task(
            self._write_audit_log(request, status_code, body_bytes, duration_ms)
        )

    async def _write_audit_log(
        self, request: Request, status_code: int, body_bytes: bytes, duration_ms: int
    ):
        """写入审计日志（异步，不阻塞响应）。"""
        try:
            from app.modules.audit.repository.models.audit_log import AuditLogDoc

            ctx = get_operation_context()
            trace = get_trace_context()

            # 未认证请求跳过（actor_id 为默认值）
            if ctx.actor_id == "-":
                return

            path = request.url.path

            # 解析请求体（高危路径不记录 body，避免密钥/口令/配置值入库）
            request_body = None if should_skip_body_logging(path) else self._parse_body(body_bytes)

            # 推断资源类型和 ID
            resource_type, resource_id = self._infer_resource(path, request.path_params)

            # 推断操作类型
            action = self._infer_action(request.method, path)

            doc = AuditLogDoc(
                actor_id=ctx.actor_id,
                username=ctx.username,
                role_ids=ctx.role_ids,
                client_ip=trace.client_ip,
                request_id=trace.request_id,
                method=request.method,
                path=path,
                query_params=redact_query_params(request.query_params),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_body=request_body,
                status_code=status_code,
                duration_ms=duration_ms,
                created_at=datetime.now(timezone.utc),
            )

            await doc.insert()

        except Exception as e:
            log.error("审计日志写入失败: {}", e)

    def _parse_body(self, body_bytes: bytes) -> dict[str, Any] | None:
        """解析请求体，脱敏敏感字段。"""
        if not body_bytes or len(body_bytes) > MAX_BODY_SIZE:
            return None

        try:
            data = json.loads(body_bytes)
            if isinstance(data, dict):
                return redact_dict(data)
            return {"_raw": str(data)[:200]}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _infer_resource(self, path: str, path_params: dict) -> tuple[str, str | None]:
        """从路径推断资源类型和资源 ID。"""
        # 匹配最长前缀
        matched_prefix = ""
        for prefix in PATH_RESOURCE_MAP:
            if path.startswith(prefix) and len(prefix) > len(matched_prefix):
                matched_prefix = prefix

        resource_type = PATH_RESOURCE_MAP.get(matched_prefix, "unknown")

        # 从路径参数提取资源 ID
        resource_id = None
        if matched_prefix:
            remaining = path[len(matched_prefix):].strip("/")
            if remaining:
                resource_id = remaining.split("/")[0]
                # 排除子操作名
                if resource_id in PATH_ACTION_OVERRIDES or resource_id in {"batch", "search"}:
                    resource_id = None

        # 从 path_params 提取
        if not resource_id and path_params:
            for key in ("case_id", "req_id", "plan_id", "item_id", "task_id", "user_id", "collection_id"):
                if key in path_params:
                    resource_id = str(path_params[key])
                    break

        return resource_type, resource_id

    def _infer_action(self, method: str, path: str) -> str:
        """推断操作类型。"""
        # 检查路径后缀覆盖
        for suffix, action in PATH_ACTION_OVERRIDES.items():
            if path.endswith(suffix):
                return action

        return METHOD_ACTION_MAP.get(method, method.lower())

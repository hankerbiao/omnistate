"""操作审计日志中间件。

记录所有写操作（POST/PUT/PATCH/DELETE）的完整审计信息：
- 操作者（actor_id / username / roles）
- 请求信息（method / path / body 脱敏后）
- 业务信息（resource_type / resource_id / action）
- 响应信息（status_code / duration_ms）

异步写入 MongoDB，不阻塞请求响应。
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.shared.context import get_operation_context, get_trace_context
from app.shared.core.logger import log


# ── 配置 ────────────────────────────────────────────────────────────────

SKIP_PATHS = {
    "/health", "/health/ready", "/health/live",
    "/docs", "/openapi.json", "/redoc",
    "/favicon.ico",
}

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

REDACT_FIELDS = {"password", "api_key", "token", "secret", "authorization"}

MAX_BODY_SIZE = 4096  # 请求体记录最大字节数

# 路径前缀 → 资源类型映射
PATH_RESOURCE_MAP: dict[str, str] = {
    "/api/v1/requirements": "requirement",
    "/api/v1/test-cases": "test_case",
    "/api/v1/automation-test-cases": "automation_test_case",
    "/api/v1/execution/tasks": "execution_task",
    "/api/v1/execution-plans": "execution_plan",
    "/api/v1/work-items": "work_item",
    "/api/v1/collections": "test_case_collection",
    "/api/v1/auth/users": "user",
    "/api/v1/auth/roles": "role",
    "/api/v1/system-configs": "system_config",
    "/api/v1/ai/polish": "ai_polish",
    "/api/v1/ai/analyze-steps": "ai_analyze_steps",
    "/api/v1/ai/generate-cases": "ai_generate_cases",
    "/api/v1/ai/review-case": "ai_review_case",
    "/api/v1/ai/recommend-cases": "ai_recommend_cases",
    "/api/v1/failure-analysis/analyze": "ai_failure_analysis",
    "/api/v1/ai-analyze": "ai_collection_analysis",
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
    "/submit-result": "submit_result",
    "/transition": "transition",
    "/polish": "ai_polish",
    "/analyze-steps": "ai_analyze_steps",
    "/generate-cases": "ai_generate_cases",
    "/review-case": "ai_review_case",
    "/recommend-cases": "ai_recommend_cases",
    "/analyze": "ai_analyze",
    "/login": "login",
}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """操作审计日志中间件。

    注册顺序：在 RequestLoggingMiddleware 之后（此时 TraceContext 已填充）。
    OperationContext 在路由依赖注入阶段填充，中间件在 call_next 之后读取。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 跳过非审计路径
        if path in SKIP_PATHS or request.method not in AUDITED_METHODS:
            return await call_next(request)

        # 读取请求体（需在路由前读，因为 body 是流式的）
        body_bytes = await request.body()

        # 重新注入 body 供路由读取
        if body_bytes:
            async def _receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = _receive

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # 异步写入审计日志
        asyncio.create_task(
            self._write_audit_log(request, response, body_bytes, duration_ms)
        )

        return response

    async def _write_audit_log(self, request: Request, response, body_bytes: bytes, duration_ms: int):
        """写入审计日志（异步，不阻塞响应）。"""
        try:
            from app.modules.audit.repository.models.audit_log import AuditLogDoc

            ctx = get_operation_context()
            trace = get_trace_context()

            # 未认证请求跳过（actor_id 为默认值）
            if ctx.actor_id == "-":
                return

            path = request.url.path

            # 解析请求体
            request_body = self._parse_body(body_bytes)

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
                query_params=dict(request.query_params),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_body=request_body,
                status_code=response.status_code,
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
                return self._redact(data)
            return {"_raw": str(data)[:200]}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _redact(self, data: dict[str, Any]) -> dict[str, Any]:
        """脱敏请求体中的敏感字段。"""
        result: dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in REDACT_FIELDS:
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = self._redact(value)
            else:
                result[key] = value
        return result

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

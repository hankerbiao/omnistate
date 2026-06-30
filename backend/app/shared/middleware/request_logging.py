"""请求追踪与日志中间件。

在请求入口创建全链路追踪上下文，注入响应头，记录请求耗时。
认证依赖注入运行后会自动设置操作者上下文（user_id, role_ids 等）。
"""

from __future__ import annotations

from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.shared.context import (
    get_trace_context,
    reset_context,
    set_trace_context,
)
from app.shared.core.logger import log

# 不记录 DEBUG 日志的路径前缀
SILENT_PATHS = {"/health", "/metrics", "/favicon.ico"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    统一请求日志中间件：
    - 注入/生成 X-Request-ID，设置追踪上下文
    - 记录请求开始与结束（含耗时）
    - 响应头注入 X-Request-ID
    - 健康检查等噪音路径静默处理
    """

    MAX_BODY_PREVIEW_CHARS = 500

    async def dispatch(self, request: Request, call_next):
        # ---- 请求前：创建追踪上下文 ----
        request_id = request.headers.get("X-Request-ID")
        client_ip = self._get_client_ip(request)
        set_trace_context(request_id=request_id, client_ip=client_ip)

        is_silent = request.url.path in SILENT_PATHS
        start = perf_counter()

        if not is_silent:
            body_preview = await self._read_body_preview(request)
            log.debug(
                "HTTP {method} {path} — start | client={client} | query={query} | body={body}",
                method=request.method,
                path=request.url.path,
                client=client_ip,
                query=request.url.query or "-",
                body=body_preview,
            )

        # ---- 执行请求 ----
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (perf_counter() - start) * 1000
            log.exception(
                "HTTP {method} {path} — FAILED | client={client} | elapsed={elapsed_ms:.2f}ms | error={error}",
                method=request.method,
                path=request.url.path,
                client=client_ip,
                elapsed_ms=elapsed_ms,
                error=exc,
            )
            reset_context()
            raise

        # ---- 请求后：记录完成，注入响应头 ----
        elapsed_ms = (perf_counter() - start) * 1000
        ctx = get_trace_context()

        # 注入 X-Request-ID 响应头
        response.headers["X-Request-ID"] = ctx.request_id
        response.headers["X-Trace-ID"] = ctx.trace_id

        if not is_silent:
            log.debug(
                "HTTP {method} {path} — done | status={status} | elapsed={elapsed_ms:.2f}ms",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed_ms=elapsed_ms,
            )

        # ---- 请求结束：重置上下文 ----
        reset_context()

        return response

    # ================================================================
    # 辅助方法
    # ================================================================

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """从请求中提取客户端 IP，优先使用 X-Forwarded-For。"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    @staticmethod
    async def _read_body_preview(request: Request) -> str:
        """安全读取请求 body 预览（不破坏后续读取）。"""
        if request.method.upper() in {"GET", "HEAD", "OPTIONS", "DELETE"}:
            return "-"

        content_type = (request.headers.get("content-type") or "").lower()
        if not any(marker in content_type for marker in ("json", "text", "form", "xml")):
            return "<binary>"

        raw_body = await request.body()
        if not raw_body:
            return "-"

        preview = raw_body.decode("utf-8", errors="replace").strip()
        if len(preview) > RequestLoggingMiddleware.MAX_BODY_PREVIEW_CHARS:
            preview = f"{preview[:RequestLoggingMiddleware.MAX_BODY_PREVIEW_CHARS]}...(truncated)"
        return preview

"""请求追踪与日志中间件。

在请求入口创建全链路追踪上下文，注入响应头，记录请求耗时。
认证依赖注入运行后会自动设置操作者上下文（user_id, role_ids 等）。
"""

from __future__ import annotations

from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Match

from app.shared.context import (
    get_trace_context,
    reset_context,
    set_trace_context,
)
from app.shared.core.logger import log
from app.shared.observability.http_metrics import http_metrics
from app.shared.security.client_ip import get_client_ip
from app.shared.security.redaction import redact_query_string, safe_body_preview

# 不记录 DEBUG 日志的路径前缀
SILENT_PATH_PREFIXES = ("/health", "/metrics", "/favicon.ico")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    统一请求日志中间件：
    - 注入/生成 X-Request-ID，设置追踪上下文
    - 记录请求开始与结束（含耗时）
    - 记录进程内 HTTP 性能指标，慢请求输出 WARNING 结构化日志
    - 响应头注入 X-Request-ID
    - 健康检查等噪音路径静默处理
    """

    MAX_BODY_PREVIEW_CHARS = 500
    DEFAULT_SLOW_REQUEST_THRESHOLD_MS = 800

    async def dispatch(self, request: Request, call_next):
        # ---- 请求前：创建追踪上下文 ----
        request_id = request.headers.get("X-Request-ID")
        client_ip = get_client_ip(request) or "unknown"
        set_trace_context(request_id=request_id, client_ip=client_ip)

        path = request.url.path
        route_path = self._route_path(request)
        is_silent = self._is_silent_path(path)
        start = perf_counter()

        if not is_silent:
            body_preview = await self._read_body_preview(request)
            query_preview = redact_query_string(request.url.query) or "-"
            log.debug(
                "HTTP {method} {path} — start | client={client} | query={query} | body={body}",
                method=request.method,
                path=path,
                client=client_ip,
                query=query_preview,
                body=body_preview,
            )

        # ---- 执行请求 ----
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (perf_counter() - start) * 1000
            self._record_request_metrics(
                method=request.method,
                path=route_path,
                raw_path=path,
                status_code=500,
                elapsed_ms=elapsed_ms,
                client_ip=client_ip,
                query=request.url.query,
                is_silent=is_silent,
            )
            log.exception(
                "HTTP {method} {path} — FAILED | client={client} | "
                "elapsed={elapsed_ms:.2f}ms | error={error}",
                method=request.method,
                path=path,
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
                path=path,
                status=response.status_code,
                elapsed_ms=elapsed_ms,
            )

        self._record_request_metrics(
            method=request.method,
            path=route_path,
            raw_path=path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            client_ip=client_ip,
            query=request.url.query,
            is_silent=is_silent,
        )

        # ---- 请求结束：重置上下文 ----
        reset_context()

        return response

    # ================================================================
    # 辅助方法
    # ================================================================

    @staticmethod
    async def _read_body_preview(request: Request) -> str:
        """生成安全请求体预览，保留该入口以兼容现有调用与测试。"""
        return await safe_body_preview(request, RequestLoggingMiddleware.MAX_BODY_PREVIEW_CHARS)

    @staticmethod
    def _is_silent_path(path: str) -> bool:
        """Return whether request logging should stay quiet for noisy infrastructure paths."""
        return path.startswith(SILENT_PATH_PREFIXES)

    @staticmethod
    def _route_path(request: Request) -> str:
        """Prefer FastAPI route templates so /users/a and /users/b share a metric bucket."""
        for route in request.app.routes:
            matches, _ = route.matches(request.scope)
            if matches == Match.FULL:
                return getattr(route, "path", request.url.path)
        return request.url.path

    @staticmethod
    def _slow_request_threshold_ms() -> int:
        try:
            from app.shared.config import get_settings

            return get_settings().logging.slow_request_threshold_ms
        except Exception:
            return RequestLoggingMiddleware.DEFAULT_SLOW_REQUEST_THRESHOLD_MS

    def _record_request_metrics(
        self,
        *,
        method: str,
        path: str,
        raw_path: str,
        status_code: int,
        elapsed_ms: float,
        client_ip: str,
        query: str,
        is_silent: bool,
    ) -> None:
        """Record request metrics and emit a dedicated slow-request event when needed."""
        http_metrics.record(method=method, path=path, status_code=status_code, elapsed_ms=elapsed_ms)
        threshold_ms = self._slow_request_threshold_ms()
        if is_silent or elapsed_ms < threshold_ms:
            return

        log.warning(
            "HTTP slow request | method={method} | path={path} | raw_path={raw_path} | "
            "status={status} | elapsed={elapsed_ms:.2f}ms | threshold={threshold_ms}ms | "
            "client={client} | query={query}",
            method=method,
            path=path,
            raw_path=raw_path,
            status=status_code,
            elapsed_ms=elapsed_ms,
            threshold_ms=threshold_ms,
            client=client_ip,
            query=redact_query_string(query) or "-",
            event="http_slow_request",
            http_method=method,
            http_path=path,
            http_raw_path=raw_path,
            http_status_code=status_code,
            duration_ms=round(elapsed_ms, 2),
            slow_threshold_ms=threshold_ms,
        )

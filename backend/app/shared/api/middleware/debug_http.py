"""Debug HTTP request logging middleware."""

from __future__ import annotations

from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.shared.core.logger import log as logger


class DebugHttpLoggingMiddleware(BaseHTTPMiddleware):
    """Log inbound HTTP requests and responses when debug mode is enabled."""

    MAX_BODY_PREVIEW_CHARS = 1000

    async def dispatch(self, request: Request, call_next):
        start = perf_counter()
        body_preview = await self._read_body_preview(request)
        client = request.client.host if request.client else "unknown"
        query_string = request.url.query or "-"
        logger.debug(
            "HTTP request started: "
            f"method={request.method}, path={request.url.path}, query={query_string}, "
            f"client={client}, body={body_preview}"
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed_ms = (perf_counter() - start) * 1000
            logger.exception(
                "HTTP request failed: "
                f"method={request.method}, path={request.url.path}, client={client}, "
                f"elapsed_ms={elapsed_ms:.2f}, error={exc}"
            )
            raise

        elapsed_ms = (perf_counter() - start) * 1000
        logger.debug(
            "HTTP request completed: "
            f"method={request.method}, path={request.url.path}, client={client}, "
            f"status_code={response.status_code}, elapsed_ms={elapsed_ms:.2f}"
        )
        return response

    async def _read_body_preview(self, request: Request) -> str:
        if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
            return "-"
        content_type = (request.headers.get("content-type") or "").lower()
        if not any(marker in content_type for marker in ("json", "text", "form", "xml")):
            return f"<{content_type or 'unknown'} body omitted>"

        raw_body = await request.body()
        if not raw_body:
            return "-"
        preview = raw_body.decode("utf-8", errors="replace").strip()
        if len(preview) > self.MAX_BODY_PREVIEW_CHARS:
            preview = f"{preview[:self.MAX_BODY_PREVIEW_CHARS]}...(truncated)"
        return preview

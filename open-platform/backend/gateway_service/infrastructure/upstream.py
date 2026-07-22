"""上游 HTTP 转发客户端。"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import time
from fastapi import Request
from typing import Mapping, Any
from starlette.datastructures import Headers

from ..config import GatewaySettings


@dataclass(slots=True)
class UpstreamResult:
    status_code: int
    headers: dict[str, str]
    body: bytes
    latency_ms: int = 0


class UpstreamClient:
    """把开放 API 请求转发到 DML 主后端。"""

    def __init__(self, settings: GatewaySettings) -> None:
        timeout = httpx.Timeout(
            timeout=settings.request_timeout_seconds,
            connect=settings.connect_timeout_seconds,
        )
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def close(self) -> None:
        await self._client.aclose()

    async def forward(
        self,
        *,
        upstream_base_url: str,
        upstream_path: str,
        request: Request,
        body: bytes,
        request_id: str,
        key_id: str,
        owner_user_id: str,
        upstream_authorization: str,
        method: str | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> UpstreamResult:
        headers = _forward_headers(request.headers)
        headers.update(
            {
                "x-request-id": request_id,
                "authorization": upstream_authorization,
                "x-open-platform-key-id": key_id,
                "x-open-platform-user-id": owner_user_id,
            }
        )
        started = time.perf_counter()
        response = await self._client.request(
            method or request.method,
            f"{upstream_base_url}{upstream_path}",
            params=params if params is not None else request.query_params,
            content=body,
            headers=headers,
        )
        latency_ms = max(1, round((time.perf_counter() - started) * 1000))
        return UpstreamResult(
            status_code=response.status_code,
            headers={
                name: value
                for name, value in response.headers.items()
                if name.lower() not in _HOP_BY_HOP_HEADERS
            },
            body=response.content,
            latency_ms=latency_ms,
        )


_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


def _forward_headers(headers: Headers) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    for name, value in headers.items():
        lowered = name.lower()
        if lowered in _HOP_BY_HOP_HEADERS or lowered == "host":
            continue
        if lowered == "authorization" or lowered.startswith("x-open-platform-"):
            continue
        forwarded[name] = value
    return forwarded

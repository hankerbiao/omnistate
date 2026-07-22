"""Adapters that let MCP tools reuse Open Platform gateway internals."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Mapping
from urllib.parse import urlencode

from starlette.datastructures import Headers, QueryParams


@dataclass(frozen=True, slots=True)
class MCPRequest:
    """Small request object that exposes the fields used by gateway internals."""

    method: str
    path: str
    headers: Headers
    query_params: QueryParams
    client: SimpleNamespace
    url: SimpleNamespace


def build_mcp_request(
    *,
    method: str,
    path: str,
    api_key: str,
    query_params: Mapping[str, str | int] | None = None,
) -> MCPRequest:
    params = QueryParams({key: str(value) for key, value in (query_params or {}).items()})
    query = urlencode(dict(params))
    return MCPRequest(
        method=method.upper(),
        path=path,
        headers=Headers({"authorization": f"Bearer {api_key}", "user-agent": "dml-open-platform-mcp"}),
        query_params=params,
        client=SimpleNamespace(host="mcp-client"),
        url=SimpleNamespace(path=path, query=query),
    )


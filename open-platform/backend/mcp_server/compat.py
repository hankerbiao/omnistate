"""Compatibility helpers for MCP clients with loose argument encoding."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP


class CompatibleFastMCP(FastMCP):
    """FastMCP variant that tolerates empty list arguments from some clients."""

    async def call_tool(self, name: str, arguments: Any) -> Any:
        return await super().call_tool(name, _normalize_tool_arguments(arguments))

    def streamable_http_app(self) -> Any:
        app = super().streamable_http_app()
        app.add_middleware(MCPArgumentsCompatibilityMiddleware)
        return app


class MCPArgumentsCompatibilityMiddleware:
    """Normalize malformed empty tool arguments before MCP protocol validation."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        updated_body = _normalize_http_body(body)
        if updated_body == body:
            await self.app(scope, _body_receive(body, receive), send)
            return

        scope = dict(scope)
        scope["headers"] = _replace_content_length(scope.get("headers", []), len(updated_body))
        await self.app(scope, _body_receive(updated_body, receive), send)


def _body_receive(body: bytes, receive: Any) -> Any:
    sent = False

    async def replay_receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return await receive()
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay_receive


def _normalize_tool_arguments(arguments: Any) -> dict[str, Any]:
    if arguments is None or arguments == []:
        return {}
    if isinstance(arguments, dict):
        return arguments
    return arguments


def _normalize_http_body(body: bytes) -> bytes:
    if not body:
        return body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body

    normalized, changed = _normalize_mcp_message_arguments(payload)
    if not changed:
        return body
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _normalize_mcp_message_arguments(payload: Any) -> tuple[Any, bool]:
    if isinstance(payload, list):
        changed = False
        normalized_items = []
        for item in payload:
            normalized_item, item_changed = _normalize_mcp_message_arguments(item)
            normalized_items.append(normalized_item)
            changed = changed or item_changed
        return normalized_items, changed

    if not isinstance(payload, dict):
        return payload, False

    params = payload.get("params")
    if payload.get("method") != "tools/call" or not isinstance(params, dict):
        return payload, False
    if params.get("arguments") not in (None, []):
        return payload, False

    normalized = dict(payload)
    normalized_params = dict(params)
    normalized_params["arguments"] = {}
    normalized["params"] = normalized_params
    return normalized, True


def _replace_content_length(
    headers: list[tuple[bytes, bytes]],
    content_length: int,
) -> list[tuple[bytes, bytes]]:
    filtered = [(key, value) for key, value in headers if key.lower() != b"content-length"]
    filtered.append((b"content-length", str(content_length).encode("ascii")))
    return filtered

"""MCP service configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from gateway_service.config import GatewaySettings


@dataclass(frozen=True, slots=True)
class MCPSettings:
    """Runtime settings for the MCP service."""

    transport: str = "stdio"
    api_key: str = ""
    host: str = "127.0.0.1"
    port: int = 8810
    path: str = "/mcp"
    enable_write_tools: bool = False
    gateway: GatewaySettings = GatewaySettings()

    @classmethod
    def from_env(cls) -> "MCPSettings":
        transport = os.getenv("DML_MCP_TRANSPORT", "stdio").strip() or "stdio"
        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("DML_MCP_TRANSPORT must be stdio or streamable-http")

        port = int(os.getenv("DML_MCP_PORT", "8810"))
        if not 1 <= port <= 65535:
            raise ValueError("DML_MCP_PORT must be between 1 and 65535")

        return cls(
            transport=transport,
            api_key=os.getenv("DML_MCP_API_KEY", "").strip(),
            host=os.getenv("DML_MCP_HOST", "127.0.0.1").strip(),
            port=port,
            path=os.getenv("DML_MCP_PATH", "/mcp").strip() or "/mcp",
            enable_write_tools=_env_bool("DML_MCP_ENABLE_WRITE_TOOLS"),
            gateway=GatewaySettings.from_env(),
        )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


"""MCP 服务配置。

MCP 进程通过 HTTP 调用现有 DML 后端，避免重复初始化 MongoDB、Kafka、Redis 等基础设施。
所有配置均使用环境变量注入，不把访问令牌写入仓库。
"""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MCPSettings:
    """MCP 服务运行配置。"""

    backend_base_url: str = "http://127.0.0.1:8801"
    backend_token: str = ""
    request_timeout_seconds: float = 15.0
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8810

    @classmethod
    def from_env(cls) -> "MCPSettings":
        """从环境变量创建配置。"""
        transport = os.getenv("DML_MCP_TRANSPORT", "stdio").strip().lower()
        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("DML_MCP_TRANSPORT must be 'stdio' or 'streamable-http'")

        timeout = float(os.getenv("DML_MCP_REQUEST_TIMEOUT", "15"))
        if timeout <= 0:
            raise ValueError("DML_MCP_REQUEST_TIMEOUT must be greater than 0")

        port = int(os.getenv("DML_MCP_PORT", "8810"))
        if not 1 <= port <= 65535:
            raise ValueError("DML_MCP_PORT must be between 1 and 65535")

        host = os.getenv("DML_MCP_HOST", "127.0.0.1").strip()
        if transport == "streamable-http" and not _is_loopback_host(host):
            raise ValueError(
                "Streamable HTTP currently supports loopback hosts only; "
                "configure MCP authentication before exposing it remotely"
            )

        return cls(
            backend_base_url=os.getenv("DML_MCP_BACKEND_URL", "http://127.0.0.1:8801").rstrip("/"),
            backend_token=os.getenv("DML_MCP_BACKEND_TOKEN", "").strip(),
            request_timeout_seconds=timeout,
            transport=transport,
            host=host,
            port=port,
        )


def _is_loopback_host(host: str) -> bool:
    """仅允许明确的本机监听地址，避免固定后端令牌被远程借用。"""
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False

#!/usr/bin/env python3
"""注册执行代理到平台。

说明：
- 默认自动采集本机 `hostname`、`ip`、`agent_id`。
- 如果传了 `agent_port` 且未传 `agent_base_url`，默认拼出 `http://<ip>:<port>`。
- 如果未显式传入 `region`，优先读取环境变量 `AGENT_REGION`，否则默认使用 `default`。
- 默认调用 `POST /api/v1/execution/agents/register`。
- 当前接口不要求鉴权；如后续接入鉴权，可在请求头中补 Authorization。
"""
from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_REGISTER_PATH = "/api/v1/execution/agents/register"


def detect_hostname() -> str:
    """获取当前主机名。"""
    return socket.gethostname()


def detect_local_ip() -> str:
    """获取当前机器的首选出口 IP。

    优先通过 UDP socket 推断默认出口网卡地址，失败时回退到 hostname 解析。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        sock.close()


def resolve_region(explicit_region: str | None) -> str:
    """解析代理区域，优先使用显式参数，其次环境变量。"""
    return explicit_region or os.getenv("AGENT_REGION") or "default"


def resolve_agent_base_url(
    explicit_base_url: str | None,
    scheme: str,
    ip: str,
    port: int | None,
) -> str | None:
    """解析代理 base_url。

    如果调用方未显式传入 base_url，但提供了端口，则按协议、IP、端口自动拼接。
    """
    if explicit_base_url:
        return explicit_base_url
    if port:
        return f"{scheme}://{ip}:{port}"
    return None


def build_register_payload(
    *,
    region: str | None = None,
    agent_id: str | None = None,
    hostname: str | None = None,
    ip: str | None = None,
    agent_port: int | None = None,
    agent_base_url: str | None = None,
    agent_base_url_scheme: str = "http",
    status: str = "ONLINE",
    heartbeat_ttl_seconds: int = 90,
) -> dict[str, Any]:
    """构建代理注册 payload。

    默认尽量自动探测本机信息，只在调用方需要覆盖默认值时再显式传参。
    """
    resolved_hostname = hostname or detect_hostname()
    resolved_ip = ip or detect_local_ip()
    resolved_agent_id = agent_id or resolved_hostname
    resolved_region = resolve_region(region)
    resolved_base_url = resolve_agent_base_url(
        explicit_base_url=agent_base_url,
        scheme=agent_base_url_scheme,
        ip=resolved_ip,
        port=agent_port,
    )

    return {
        "agent_id": resolved_agent_id,
        "hostname": resolved_hostname,
        "ip": resolved_ip,
        "port": agent_port,
        "base_url": resolved_base_url,
        "region": resolved_region,
        "status": status,
        "heartbeat_ttl_seconds": heartbeat_ttl_seconds,
    }


def register_agent_to_platform(
    *,
    platform_url: str,
    register_path: str = DEFAULT_REGISTER_PATH,
    region: str | None = None,
    agent_id: str | None = None,
    hostname: str | None = None,
    ip: str | None = None,
    agent_port: int | None = None,
    agent_base_url: str | None = None,
    agent_base_url_scheme: str = "http",
    status: str = "ONLINE",
    heartbeat_ttl_seconds: int = 90,
    timeout: int = 10,
) -> dict[str, Any]:
    """向平台发送代理注册请求并返回响应 JSON。"""
    payload = build_register_payload(
        region=region,
        agent_id=agent_id,
        hostname=hostname,
        ip=ip,
        agent_port=agent_port,
        agent_base_url=agent_base_url,
        agent_base_url_scheme=agent_base_url_scheme,
        status=status,
        heartbeat_ttl_seconds=heartbeat_ttl_seconds,
    )
    url = f"{platform_url.rstrip('/')}{register_path}"
    response = requests.post(url, json=payload, timeout=timeout)
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"注册失败: status={response.status_code}, body={response.text}")
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}


def main() -> None:
    """本地运行示例。

    使用前可按需设置：
    - AGENT_PLATFORM_URL: 平台地址，默认 http://127.0.0.1:8000
    - AGENT_REGION: 代理区域，默认 default
    - AGENT_PORT: 代理服务端口，用于自动拼接 base_url
    """
    platform_url = os.getenv("AGENT_PLATFORM_URL", "http://127.0.0.1:8000")
    agent_port_raw = os.getenv("AGENT_PORT")
    agent_port = int(agent_port_raw) if agent_port_raw else None

    result = register_agent_to_platform(
        platform_url=platform_url,
        agent_port=agent_port,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

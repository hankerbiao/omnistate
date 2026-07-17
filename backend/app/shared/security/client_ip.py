"""可信代理感知的客户端 IP 解析。"""
from __future__ import annotations

from ipaddress import ip_address, ip_network
from typing import Iterable

from starlette.requests import Request

from app.shared.config import get_settings


def _is_trusted(host: str, trusted_proxies: Iterable[str]) -> bool:
    try:
        address = ip_address(host)
    except ValueError:
        return False
    for proxy in trusted_proxies:
        try:
            if address in ip_network(proxy, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request) -> str | None:
    """仅当直连节点可信时解析 X-Forwarded-For，否则返回连接来源。"""
    direct_ip = request.client.host if request.client else None
    if not direct_ip:
        return None

    trusted_proxies = get_settings().app.trusted_proxies
    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded or not _is_trusted(direct_ip, trusted_proxies):
        return direct_ip

    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    chain.append(direct_ip)
    for candidate in reversed(chain):
        if not _is_trusted(candidate, trusted_proxies):
            return candidate
    return chain[0] if chain else direct_ip

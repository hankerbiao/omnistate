"""可信代理客户端 IP 解析测试。"""
from __future__ import annotations

from types import SimpleNamespace

import app.shared.security.client_ip as client_ip_mod
from app.shared.security.client_ip import get_client_ip


class _Request:
    def __init__(self, direct_ip: str, forwarded: str | None = None):
        self.client = SimpleNamespace(host=direct_ip)
        self.headers = {"X-Forwarded-For": forwarded} if forwarded else {}


def _settings(trusted_proxies: list[str]):
    return SimpleNamespace(app=SimpleNamespace(trusted_proxies=trusted_proxies))


def test_untrusted_direct_client_cannot_spoof_forwarded_for(monkeypatch):
    monkeypatch.setattr(client_ip_mod, "get_bootstrap_settings", lambda: _settings([]))

    assert get_client_ip(_Request("203.0.113.5", "10.0.0.8")) == "203.0.113.5"


def test_trusted_proxy_uses_forwarded_client(monkeypatch):
    monkeypatch.setattr(
        client_ip_mod,
        "get_bootstrap_settings",
        lambda: _settings(["10.0.0.0/8"]),
    )

    assert get_client_ip(_Request("10.0.0.5", "203.0.113.8")) == "203.0.113.8"


def test_proxy_chain_skips_trusted_hops_from_right(monkeypatch):
    monkeypatch.setattr(
        client_ip_mod,
        "get_bootstrap_settings",
        lambda: _settings(["10.0.0.0/8", "192.168.0.0/16"]),
    )

    request = _Request("10.0.0.5", "203.0.113.8, 192.168.1.10")
    assert get_client_ip(request) == "203.0.113.8"

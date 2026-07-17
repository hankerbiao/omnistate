"""就绪检查（真实 Readiness）单元测试。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.shared.api.routes.health as health_mod
import app.shared.redis.service as redis_service
from app.shared.api.routes.health import router as health_router


class _FakeAdmin:
    def __init__(self, ok: bool):
        self._ok = ok

    async def command(self, cmd):
        if not self._ok:
            raise RuntimeError("mongo down")
        return {}


class _FakeMongo:
    def __init__(self, ok: bool):
        self._ok = ok

    @property
    def admin(self):
        return _FakeAdmin(self._ok)


class _FakeRedis:
    def __init__(self, ok: bool):
        self._ok = ok

    def ping(self):
        if not self._ok:
            raise RuntimeError("redis down")
        return True


def _fake_registry():
    class _Reg:
        async def health_check(self):
            return {"components": {}, "timestamp": "2026-07-17T00:00:00+00:00"}

    return _Reg()


def test_readiness_ready_when_mongo_ok_and_redis_unconfigured(monkeypatch):
    monkeypatch.setattr(health_mod, "get_mongo_client", lambda: _FakeMongo(ok=True))
    monkeypatch.setattr(redis_service, "redis_conn", None)
    monkeypatch.setattr(health_mod, "get_infrastructure_registry", _fake_registry)

    app = FastAPI()
    app.include_router(health_router, prefix="/health")
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "ready"
    comp = resp.json()["data"]["components"]
    assert comp["mongodb"]["status"] == "healthy"
    assert comp["redis"]["status"] == "not_configured"


def test_readiness_503_when_mongo_down(monkeypatch):
    monkeypatch.setattr(health_mod, "get_mongo_client", lambda: _FakeMongo(ok=False))
    monkeypatch.setattr(redis_service, "redis_conn", None)
    monkeypatch.setattr(health_mod, "get_infrastructure_registry", _fake_registry)

    app = FastAPI()
    app.include_router(health_router, prefix="/health")
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["data"]["status"] == "not_ready"
    assert resp.json()["data"]["components"]["mongodb"]["status"] == "error"


def test_readiness_503_when_redis_enabled_but_down(monkeypatch):
    monkeypatch.setattr(health_mod, "get_mongo_client", lambda: _FakeMongo(ok=True))
    monkeypatch.setattr(redis_service, "redis_conn", _FakeRedis(ok=False))
    monkeypatch.setattr(health_mod, "get_infrastructure_registry", _fake_registry)

    app = FastAPI()
    app.include_router(health_router, prefix="/health")
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["data"]["components"]["redis"]["status"] == "error"


def test_readiness_ready_when_redis_enabled_and_ok(monkeypatch):
    monkeypatch.setattr(health_mod, "get_mongo_client", lambda: _FakeMongo(ok=True))
    monkeypatch.setattr(redis_service, "redis_conn", _FakeRedis(ok=True))
    monkeypatch.setattr(health_mod, "get_infrastructure_registry", _fake_registry)

    app = FastAPI()
    app.include_router(health_router, prefix="/health")
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["data"]["components"]["redis"]["status"] == "healthy"

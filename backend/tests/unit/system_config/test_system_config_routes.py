"""系统配置路由权限与静态路由优先级测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.system_config.api.routes import router
from app.modules.system_config.service import ConfigService
from app.shared.auth import get_current_user


async def fake_regular_user():
    return {"user_id": "user-001", "username": "regular", "role_ids": ["USER"]}


async def fake_admin_user():
    return {"user_id": "admin-001", "username": "admin", "role_ids": ["ADMIN"]}


def _build_client(current_user_override=None) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    if current_user_override is not None:
        app.dependency_overrides[get_current_user] = current_user_override
    return TestClient(app)


def test_system_config_routes_require_authentication():
    client = _build_client()

    response = client.get("/system-configs/categories")

    assert response.status_code == 401


def test_system_config_routes_reject_user_without_permission(monkeypatch):
    async def no_permissions(user_id: str) -> list[str]:
        return []

    monkeypatch.setattr("app.shared.auth.jwt_auth.get_user_permissions", no_permissions)
    client = _build_client(fake_regular_user)

    response = client.get("/system-configs/categories")

    assert response.status_code == 403


def test_system_config_routes_allow_admin(monkeypatch):
    async def fake_categories() -> list[str]:
        return ["ai", "system"]

    monkeypatch.setattr(ConfigService, "get_categories", fake_categories)
    client = _build_client(fake_admin_user)

    response = client.get("/system-configs/categories")

    assert response.status_code == 200
    assert response.json()["data"] == ["ai", "system"]


def test_batch_update_uses_static_batch_route(monkeypatch):
    calls: list[dict] = []

    async def fake_batch_update(*, items, changed_by, remark):
        calls.append({"items": items, "changed_by": changed_by, "remark": remark})
        return len(items)

    monkeypatch.setattr(ConfigService, "batch_update", fake_batch_update)
    client = _build_client(fake_admin_user)

    response = client.put(
        "/system-configs/batch",
        json={
            "items": [{"config_key": "ai.model", "config_value": "model-v2"}],
            "remark": "route regression",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["updated_count"] == 1
    assert calls == [
        {
            "items": [{"config_key": "ai.model", "config_value": "model-v2"}],
            "changed_by": "admin",
            "remark": "route regression",
        }
    ]


def _config_doc(*, key: str, value: str):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id="cfg-1",
        config_key=key,
        config_value=value,
        config_type="string",
        category="system",
        description="secret",
        is_active=True,
        needs_restart=True,
        created_at=now,
        updated_at=now,
        updated_by="admin",
    )


def test_config_detail_returns_plain_value(monkeypatch):
    async def fake_get_config_by_key(_key):
        return _config_doc(key="redis.password", value="plain-secret")

    monkeypatch.setattr(ConfigService, "get_config_by_key", fake_get_config_by_key)
    client = _build_client(fake_admin_user)

    response = client.get("/system-configs/redis.password")

    assert response.status_code == 200
    assert response.json()["data"]["config_value"] == "plain-secret"


def test_config_history_returns_plain_values(monkeypatch):
    now = datetime.now(timezone.utc)

    async def fake_history(*, config_key, limit):
        return [
            SimpleNamespace(
                id="history-1",
                config_key="redis.password",
                old_value="old-secret",
                new_value="new-secret",
                changed_by="admin",
                changed_at=now,
                remark=None,
            )
        ]

    monkeypatch.setattr(ConfigService, "get_history", fake_history)
    client = _build_client(fake_admin_user)

    response = client.get("/system-configs/history")

    assert response.status_code == 200
    assert response.json()["data"][0]["old_value"] == "old-secret"
    assert response.json()["data"][0]["new_value"] == "new-secret"

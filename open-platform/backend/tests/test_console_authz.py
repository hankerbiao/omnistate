"""Tests for console user scoping and API key ownership."""

from __future__ import annotations

from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from gateway_service.app import create_app
from gateway_service.config import GatewaySettings
from gateway_service.domain.models import UserQuota
from gateway_service.infrastructure.repository import GatewayRepository


CONSOLE_TOKEN = "dev-console-token"


def _client() -> tuple[TemporaryDirectory[str], TestClient]:
    tmp = TemporaryDirectory()
    settings = GatewaySettings(db_path=f"{tmp.name}/gateway.db", console_token=CONSOLE_TOKEN)
    return tmp, TestClient(create_app(settings))


def _headers(user_id: str) -> dict[str, str]:
    return {"x-console-token": CONSOLE_TOKEN, "x-console-user-id": user_id}


def test_default_admin_can_login() -> None:
    tmp, client = _client()
    with tmp:
        response = client.post(
            "/api/v1/open-platform/login",
            json={"username": "admin", "password": "admin123"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["user"]["id"] == "user_admin"


def test_login_rejects_invalid_password() -> None:
    tmp, client = _client()
    with tmp:
        response = client.post(
            "/api/v1/open-platform/login",
            json={"username": "admin", "password": "wrong-password"},
        )

    assert response.status_code == 401


def test_admin_can_create_console_user() -> None:
    tmp, client = _client()
    with tmp:
        response = client.post(
            "/api/v1/open-platform/users",
            headers=_headers("user_admin"),
            json={
                "username": "newdev",
                "role": "developer",
                "allowedCapabilityIds": ["cap_list_tasks"],
                "quota": {"enabled": True, "monthlyLimit": 1000, "rpmLimit": 60, "concurrency": 5},
            },
        )
        login_response = client.post(
            "/api/v1/open-platform/login",
            json={"username": "newdev", "password": "123456"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["username"] == "newdev"
    assert response.json()["data"]["name"] == "newdev"
    assert response.json()["data"]["team"] == "未分组"
    assert response.json()["data"]["mustChangePassword"] is True
    assert login_response.status_code == 200
    assert login_response.json()["data"]["user"]["mustChangePassword"] is True


def test_new_user_must_change_default_password_before_console_operations() -> None:
    tmp, client = _client()
    with tmp:
        create_response = client.post(
            "/api/v1/open-platform/users",
            headers=_headers("user_admin"),
            json={"username": "mustchange", "role": "developer"},
        )
        user_id = create_response.json()["data"]["id"]

        blocked_response = client.get("/api/v1/open-platform/keys", headers=_headers(user_id))
        reject_default_response = client.post(
            "/api/v1/open-platform/change-password",
            headers=_headers(user_id),
            json={"oldPassword": "123456", "newPassword": "123456"},
        )
        change_response = client.post(
            "/api/v1/open-platform/change-password",
            headers=_headers(user_id),
            json={"oldPassword": "123456", "newPassword": "newpass123"},
        )
        allowed_response = client.get("/api/v1/open-platform/keys", headers=_headers(user_id))
        login_response = client.post(
            "/api/v1/open-platform/login",
            json={"username": "mustchange", "password": "newpass123"},
        )

    assert blocked_response.status_code == 403
    assert blocked_response.json()["detail"] == "Password change required"
    assert reject_default_response.status_code == 400
    assert change_response.status_code == 200
    assert change_response.json()["data"]["user"]["mustChangePassword"] is False
    assert allowed_response.status_code == 200
    assert login_response.status_code == 200
    assert login_response.json()["data"]["user"]["mustChangePassword"] is False


def test_non_admin_cannot_create_console_user() -> None:
    tmp, client = _client()
    with tmp:
        response = client.post(
            "/api/v1/open-platform/users",
            headers=_headers("user_developer"),
            json={
                "username": "blocked",
                "role": "developer",
            },
        )

    assert response.status_code == 403


def test_console_key_list_is_scoped_to_current_non_admin_user() -> None:
    tmp, client = _client()
    with tmp:
        admin_response = client.get("/api/v1/open-platform/keys", headers=_headers("user_admin"))
        developer_response = client.get("/api/v1/open-platform/keys", headers=_headers("user_developer"))

    assert admin_response.status_code == 200
    assert developer_response.status_code == 200
    admin_keys = admin_response.json()["data"]
    developer_keys = developer_response.json()["data"]
    assert len(admin_keys) == 4
    assert {key["ownerUserId"] for key in developer_keys} == {"user_developer"}


def test_current_user_capabilities_are_scoped_and_include_api_details() -> None:
    tmp, client = _client()
    with tmp:
        response = client.get(
            "/api/v1/open-platform/me/capabilities",
            headers=_headers("user_developer"),
        )

    assert response.status_code == 200
    data = response.json()["data"]
    capability_ids = {item["id"] for item in data["capabilities"]}
    assert data["user"]["id"] == "user_developer"
    assert capability_ids == {"cap_list_tasks", "cap_task_status", "cap_report"}
    task_status = next(item for item in data["capabilities"] if item["id"] == "cap_task_status")
    assert task_status["method"] == "GET"
    assert task_status["description"]
    assert task_status["params"][0]["name"] == "task_id"
    assert task_status["params"][0]["type"] == "string"


def test_non_admin_cannot_manage_other_users_or_their_keys() -> None:
    tmp, client = _client()
    with tmp:
        users_response = client.get("/api/v1/open-platform/users", headers=_headers("user_developer"))
        delete_response = client.delete(
            "/api/v1/open-platform/keys/key_01",
            headers=_headers("user_developer"),
        )

    assert users_response.status_code == 403
    assert delete_response.status_code == 404


def test_non_admin_create_key_ignores_forged_owner_user_id() -> None:
    tmp, client = _client()
    with tmp:
        response = client.post(
            "/api/v1/open-platform/keys",
            headers=_headers("user_developer"),
            json={
                "name": "开发者自建",
                "env": "test",
                "scopes": ["execution_tasks:read"],
                "ownerUserId": "user_admin",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["key"]["ownerUserId"] == "user_developer"


def test_created_key_maps_console_user_to_dml_upstream_subject() -> None:
    repository = GatewayRepository(default_quota=UserQuota())

    admin_key = repository.create_key(
        name="admin key",
        env="live",
        scopes=["test_cases:read"],
        owner_user_id="user_admin",
    ).key
    developer_key = repository.create_key(
        name="developer key",
        env="live",
        scopes=["test_cases:read"],
        owner_user_id="user_developer",
    ).key

    assert admin_key.upstreamUserId == "admin"
    assert developer_key.upstreamUserId == "dev"

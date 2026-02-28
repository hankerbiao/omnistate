import pytest

from app.shared.auth import jwt_auth


PROTECTED_ENDPOINTS = [
    ("GET", "/api/v1/work-items/types"),
    ("DELETE", "/api/v1/assets/components/PN-001"),
    ("GET", "/api/v1/requirements"),
    ("DELETE", "/api/v1/test-cases/CASE-001"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_business_routes_require_authentication(client, method: str, path: str):
    response = client.request(method, path)

    assert response.status_code == 401
    payload = response.json()
    assert payload["code"] == 401
    assert payload["message"] == "HTTP Error 401"
    assert payload["data"]["detail"] == "Not authenticated"


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_business_routes_reject_insufficient_permissions(
    app,
    client,
    monkeypatch,
    method: str,
    path: str,
):
    async def _fake_current_user():
        return {"user_id": "no-permission-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return []

    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)

    response = client.request(method, path, headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 403
    payload = response.json()
    assert payload["code"] == 403
    assert payload["message"] == "HTTP Error 403"
    assert payload["data"]["detail"] == "permission denied"

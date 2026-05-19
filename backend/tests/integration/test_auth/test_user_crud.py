"""User CRUD API tests."""
import pytest
from httpx import AsyncClient

from tests.integration.utils.helpers import create_user_data, unique_id


@pytest.mark.asyncio
async def test_admin_create_user(client_admin: AsyncClient):
    """2.1 - ADMIN can create user with users:write permission."""
    user_data = create_user_data()
    resp = await client_admin.post("/api/v1/auth/users", json=user_data)
    assert resp.status_code == 201, f"Create user failed: {resp.text}"
    data = resp.json()["data"]
    assert data["user_id"] == user_data["user_id"]


@pytest.mark.asyncio
async def test_non_admin_create_user_forbidden(client_tester: AsyncClient):
    """2.2 - Non-ADMIN cannot create user without users:write permission."""
    user_data = create_user_data()
    resp = await client_tester.post("/api/v1/auth/users", json=user_data)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_users(client_admin: AsyncClient):
    """2.3 - Query user list should return 200."""
    resp = await client_admin.get("/api/v1/auth/users")
    assert resp.status_code == 200, f"List users failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_users_filter_by_role(client_admin: AsyncClient):
    """2.4 - Query users filtered by role_id should return 200."""
    resp = await client_admin.get("/api/v1/auth/users?role_id=TPM")
    assert resp.status_code == 200, f"Filter users failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_user_detail(client_admin: AsyncClient, test_users):
    """2.5 - Get user detail should return 200."""
    user_id = test_users["TPM"]["user_id"]
    resp = await client_admin.get(f"/api/v1/auth/users/{user_id}")
    assert resp.status_code == 200, f"Get user failed: {resp.text}"
    data = resp.json()["data"]
    assert data["user_id"] == user_id


@pytest.mark.asyncio
async def test_update_user(client_admin: AsyncClient, test_users):
    """2.6 - Update user info should return 200."""
    user_id = test_users["TPM"]["user_id"]
    resp = await client_admin.put(
        f"/api/v1/auth/users/{user_id}",
        json={"username": "Updated TPM Name"},
    )
    assert resp.status_code == 200, f"Update user failed: {resp.text}"


@pytest.mark.asyncio
async def test_admin_update_user_roles(client_admin: AsyncClient, test_users):
    """2.7 - ADMIN can update user roles."""
    user_id = test_users["TPM"]["user_id"]
    resp = await client_admin.patch(
        f"/api/v1/auth/users/{user_id}/roles",
        json={"role_ids": ["TPM", "REVIEWER"]},
    )
    assert resp.status_code == 200, f"Update roles failed: {resp.text}"
    data = resp.json()["data"]
    assert "REVIEWER" in data["role_ids"]


@pytest.mark.asyncio
async def test_non_admin_update_user_roles_forbidden(client_tpm: AsyncClient, test_users):
    """2.8 - Non-ADMIN cannot update user roles."""
    user_id = test_users["REVIEWER"]["user_id"]
    resp = await client_tpm.patch(
        f"/api/v1/auth/users/{user_id}/roles",
        json={"role_ids": ["TESTER"]},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
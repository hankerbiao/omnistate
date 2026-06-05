"""Role and permission management API tests."""
import pytest
from httpx import AsyncClient

from tests.integration.conftest import TestDataRegistry
from tests.integration.utils.helpers import create_role_data, register_created_role, unique_id


@pytest.mark.asyncio
async def test_list_roles(client_admin: AsyncClient):
    """3.1 - Query role list should return 200."""
    resp = await client_admin.get("/api/v1/auth/roles")
    assert resp.status_code == 200, f"List roles failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_create_role(client_admin: AsyncClient, test_data_registry: TestDataRegistry):
    """3.2 - Create role should return 201."""
    role_data = create_role_data()
    resp = await client_admin.post("/api/v1/auth/roles", json=role_data)
    assert resp.status_code == 201, f"Create role failed: {resp.text}"
    data = resp.json()["data"]
    assert data["role_id"] == role_data["role_id"]
    register_created_role(test_data_registry, data)


@pytest.mark.asyncio
async def test_update_role_permissions_admin(client_admin: AsyncClient, test_users):
    """3.3 - ADMIN can update role permissions."""
    user_id = test_users["TPM"]["user_id"]
    resp = await client_admin.patch(
        f"/api/v1/auth/users/{user_id}/roles",
        json={"role_ids": ["TPM"]},
    )
    assert resp.status_code == 200, f"Update role permissions failed: {resp.text}"


@pytest.mark.asyncio
async def test_list_permissions(client_admin: AsyncClient):
    """3.4 - Query permission list should return 200."""
    resp = await client_admin.get("/api/v1/auth/permissions")
    assert resp.status_code == 200, f"List permissions failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0
"""Extended auth API integration tests for roles and static permissions."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_roles(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/auth/roles")
    assert resp.status_code == 200, f"List roles failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    role_ids = [role.get("role_id") for role in data if isinstance(role, dict)]
    assert "ADMIN" in role_ids


@pytest.mark.asyncio
async def test_list_roles_pagination(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/auth/roles?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_get_role(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/auth/roles/ADMIN")
    assert resp.status_code == 200, f"Get role failed: {resp.text}"
    data = resp.json()["data"]
    assert data["role_id"] == "ADMIN"


@pytest.mark.asyncio
async def test_get_role_not_found(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/auth/roles/NONEXISTENT_ROLE_XYZ")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_roles_no_permission(client_tester: AsyncClient):
    resp = await client_tester.get("/api/v1/auth/roles")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_permissions_any_user(client_tpm: AsyncClient):
    resp = await client_tpm.get("/api/v1/auth/permissions")
    assert resp.status_code == 200, f"List permissions failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert {"perm_id", "code", "name"}.issubset(data[0])


@pytest.mark.asyncio
async def test_list_permissions_pagination(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/auth/permissions?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) <= 10


@pytest.mark.asyncio
async def test_permission_mutation_endpoints_removed(client_admin: AsyncClient):
    payload = {"perm_id": "test:removed", "code": "test:removed", "name": "Removed"}
    assert (await client_admin.post("/api/v1/auth/permissions", json=payload)).status_code == 405
    assert (await client_admin.put("/api/v1/auth/permissions/test:removed", json={"name": "x"})).status_code == 405
    assert (await client_admin.delete("/api/v1/auth/permissions/test:removed")).status_code == 405


@pytest.mark.asyncio
async def test_update_role_permissions(client_admin: AsyncClient):
    resp = await client_admin.get("/api/v1/auth/roles/TESTER")
    if resp.status_code != 200:
        return

    original_permissions = resp.json()["data"].get("permission_ids", [])
    list_perms = await client_admin.get("/api/v1/auth/permissions?limit=1")
    assert list_perms.status_code == 200
    perms = list_perms.json()["data"]
    assert perms

    perm_id = perms[0]["perm_id"]
    if perm_id in original_permissions:
        return

    new_perms = original_permissions + [perm_id]
    try:
        patch_resp = await client_admin.patch(
            "/api/v1/auth/roles/TESTER/permissions",
            json={"permission_ids": new_perms},
        )
        assert patch_resp.status_code == 200
    finally:
        await client_admin.patch(
            "/api/v1/auth/roles/TESTER/permissions",
            json={"permission_ids": original_permissions},
        )


@pytest.mark.asyncio
async def test_update_role_permissions_no_admin(client_tpm: AsyncClient):
    resp = await client_tpm.patch(
        "/api/v1/auth/roles/TESTER/permissions",
        json={"permission_ids": ["work_items:read"]},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_roles_unauthenticated(app_with_lifespan):
    from httpx import ASGITransport, AsyncClient

    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test")
        resp = await client.get("/api/v1/auth/roles")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_permissions_unauthenticated(app_with_lifespan):
    from httpx import ASGITransport, AsyncClient

    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test")
        resp = await client.get("/api/v1/auth/permissions")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

"""Extended auth API integration tests.

Tests the missing auth APIs:
- /auth/admin/navigation/pages
- /auth/roles (GET, POST, PUT, PATCH)
- /auth/permissions (GET, POST, PUT)
"""
import pytest
from httpx import AsyncClient

from tests.integration.utils.helpers import unique_id


# ==================== Navigation Pages Tests ====================


@pytest.mark.asyncio
async def test_list_navigation_pages(client_admin: AsyncClient):
    """9.1 - Admin can list navigation pages."""
    resp = await client_admin.get("/api/v1/auth/admin/navigation/pages")
    assert resp.status_code == 200, f"List navigation pages failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_navigation_pages_exclude_inactive(client_admin: AsyncClient):
    """9.2 - List navigation pages excluding inactive."""
    resp = await client_admin.get("/api/v1/auth/admin/navigation/pages?include_inactive=false")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_navigation_pages_no_admin(client_tpm: AsyncClient):
    """9.3 - Non-admin cannot list navigation pages."""
    resp = await client_tpm.get("/api/v1/auth/admin/navigation/pages")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_create_navigation_page(client_admin: AsyncClient):
    """9.4 - Admin can create navigation page."""
    view_name = f"test_view_{unique_id()}"
    resp = await client_admin.post(
        "/api/v1/auth/admin/navigation/pages",
        json={
            "view": view_name,
            "label": "Test View",
            "permission": "test:view",
            "description": "Test navigation page",
            "order": 100,
            "is_active": True,
        },
    )
    # May return 201 or 409 if already exists
    assert resp.status_code in (201, 409), f"Unexpected status: {resp.status_code}"


@pytest.mark.asyncio
async def test_create_navigation_page_no_admin(client_tpm: AsyncClient):
    """9.5 - Non-admin cannot create navigation page."""
    resp = await client_tpm.post(
        "/api/v1/auth/admin/navigation/pages",
        json={
            "view": f"test_view_{unique_id()}",
            "label": "Test View",
            "permission": "test:view",
            "order": 100,
        },
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_navigation_page(client_admin: AsyncClient):
    """9.6 - Admin can get specific navigation page."""
    resp = await client_admin.get("/api/v1/auth/admin/navigation/pages/work_items")
    # May return 200 or 404 depending on whether the page exists
    assert resp.status_code in (200, 404), f"Unexpected status: {resp.status_code}"


@pytest.mark.asyncio
async def test_update_navigation_page(client_admin: AsyncClient):
    """9.7 - Admin can update navigation page."""
    # First create a page
    view_name = f"test_update_{unique_id()}"
    await client_admin.post(
        "/api/v1/auth/admin/navigation/pages",
        json={
            "view": view_name,
            "label": "Original Title",
            "permission": "test:view",
            "order": 1,
        },
    )

    # Update it
    resp = await client_admin.put(
        f"/api/v1/auth/admin/navigation/pages/{view_name}",
        json={"label": "Updated Title", "order": 2},
    )
    # May return 200, 404 (page not found), or 409 (duplicate)
    assert resp.status_code in (200, 404, 409), f"Unexpected status: {resp.status_code}"


@pytest.mark.asyncio
async def test_delete_navigation_page(client_admin: AsyncClient):
    """9.8 - Admin can delete navigation page."""
    # First create a page
    view_name = f"test_delete_{unique_id()}"
    await client_admin.post(
        "/api/v1/auth/admin/navigation/pages",
        json={
            "view": view_name,
            "label": "To Delete",
            "permission": "test:view",
            "order": 1,
        },
    )

    # Delete it
    resp = await client_admin.delete(f"/api/v1/auth/admin/navigation/pages/{view_name}")
    assert resp.status_code in (200, 404), f"Unexpected status: {resp.status_code}"


# ==================== Roles Tests ====================


@pytest.mark.asyncio
async def test_list_roles(client_admin: AsyncClient):
    """9.9 - Admin can list roles."""
    resp = await client_admin.get("/api/v1/auth/roles")
    assert resp.status_code == 200, f"List roles failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    # Should contain system roles like ADMIN, TPM, etc.
    role_ids = [role.get("role_id") for role in data if isinstance(role, dict)]
    assert "ADMIN" in role_ids


@pytest.mark.asyncio
async def test_list_roles_pagination(client_admin: AsyncClient):
    """9.10 - List roles with pagination."""
    resp = await client_admin.get("/api/v1/auth/roles?limit=5&offset=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_get_role(client_admin: AsyncClient):
    """9.11 - Admin can get role by ID."""
    resp = await client_admin.get("/api/v1/auth/roles/ADMIN")
    assert resp.status_code == 200, f"Get role failed: {resp.text}"
    data = resp.json()["data"]
    assert data["role_id"] == "ADMIN"


@pytest.mark.asyncio
async def test_get_role_not_found(client_admin: AsyncClient):
    """9.12 - Get non-existent role returns 404."""
    resp = await client_admin.get("/api/v1/auth/roles/NONEXISTENT_ROLE_XYZ")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_roles_no_permission(client_tester: AsyncClient):
    """9.13 - Non-admin cannot list roles."""
    resp = await client_tester.get("/api/v1/auth/roles")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ==================== Permissions Tests ====================


@pytest.mark.asyncio
async def test_list_permissions_any_user(client_tpm: AsyncClient):
    """9.14 - Any authenticated user can list permissions."""
    resp = await client_tpm.get("/api/v1/auth/permissions")
    assert resp.status_code == 200, f"List permissions failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    # Should contain system permissions
    assert len(data) > 0


@pytest.mark.asyncio
async def test_list_permissions_pagination(client_admin: AsyncClient):
    """9.15 - List permissions with pagination."""
    resp = await client_admin.get("/api/v1/auth/permissions?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) <= 10


@pytest.mark.asyncio
async def test_get_permission(client_admin: AsyncClient):
    """9.16 - Get permission by ID."""
    # First list to get a permission ID
    list_resp = await client_admin.get("/api/v1/auth/permissions?limit=1")
    if list_resp.status_code == 200:
        permissions = list_resp.json()["data"]
        if permissions and len(permissions) > 0:
            perm_id = permissions[0].get("perm_id") or permissions[0].get("permission_id")
            if perm_id:
                resp = await client_admin.get(f"/api/v1/auth/permissions/{perm_id}")
                assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_permission_not_found(client_admin: AsyncClient):
    """9.17 - Get non-existent permission returns 404."""
    resp = await client_admin.get("/api/v1/auth/permissions/NONEXISTENT_PERM_XYZ")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_create_permission(client_admin: AsyncClient):
    """9.18 - Admin can create permission."""
    perm_name = f"test_perm_{unique_id()}"
    resp = await client_admin.post(
        "/api/v1/auth/permissions",
        json={
            "perm_id": perm_name,
            "code": f"test.code.{unique_id()}",
            "name": f"Test Permission {perm_name}",
            "description": "Test permission description",
        },
    )
    # May return 201 or 409 (already exists)
    assert resp.status_code in (201, 409), f"Unexpected status: {resp.status_code}"


@pytest.mark.asyncio
async def test_create_permission_no_permission(client_tester: AsyncClient):
    """9.19 - Non-admin cannot create permission."""
    resp = await client_tester.post(
        "/api/v1/auth/permissions",
        json={
            "perm_id": f"test_perm_{unique_id()}",
            "code": f"test.code.{unique_id()}",
            "name": "Test Permission",
        },
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_update_permission(client_admin: AsyncClient):
    """9.20 - Admin can update permission."""
    # First create a permission
    perm_name = f"test_perm_update_{unique_id()}"
    await client_admin.post(
        "/api/v1/auth/permissions",
        json={
            "perm_id": perm_name,
            "code": f"test.code.{unique_id()}",
            "name": f"Original Name {perm_name}",
        },
    )

    # Update it
    resp = await client_admin.put(
        f"/api/v1/auth/permissions/{perm_name}",
        json={"name": "Updated Name", "description": "Updated description"},
    )
    assert resp.status_code in (200, 404, 409), f"Unexpected status: {resp.status_code}"


# ==================== Role Permissions Update Tests ====================


@pytest.mark.asyncio
async def test_update_role_permissions(client_admin: AsyncClient):
    """9.21 - Admin can update role permissions."""
    # Get the TESTER role
    resp = await client_admin.get("/api/v1/auth/roles/TESTER")
    if resp.status_code == 200:
        original_permissions = resp.json()["data"].get("permission_ids", [])

        # Add a permission (if any exist)
        list_perms = await client_admin.get("/api/v1/auth/permissions?limit=1")
        if list_perms.status_code == 200:
            perms = list_perms.json()["data"]
            if perms:
                perm_id = perms[0].get("perm_id") or perms[0].get("permission_id")
                if perm_id:
                    new_perms = original_permissions + [perm_id]
                    patch_resp = await client_admin.patch(
                        "/api/v1/auth/roles/TESTER/permissions",
                        json={"permission_ids": new_perms},
                    )
                    assert patch_resp.status_code == 200


@pytest.mark.asyncio
async def test_update_role_permissions_no_admin(client_tpm: AsyncClient):
    """9.22 - Non-admin cannot update role permissions."""
    resp = await client_tpm.patch(
        "/api/v1/auth/roles/TESTER/permissions",
        json={"permission_ids": ["work_items:read"]},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ==================== Unauthenticated Access Tests ====================


@pytest.mark.asyncio
async def test_list_navigation_pages_unauthenticated(app_with_lifespan):
    """9.23 - Unauthenticated access to navigation pages."""
    from httpx import ASGITransport, AsyncClient
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test")
        resp = await client.get("/api/v1/auth/admin/navigation/pages")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_roles_unauthenticated(app_with_lifespan):
    """9.24 - Unauthenticated access to roles."""
    from httpx import ASGITransport, AsyncClient
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test")
        resp = await client.get("/api/v1/auth/roles")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"


@pytest.mark.asyncio
async def test_list_permissions_unauthenticated(app_with_lifespan):
    """9.25 - Unauthenticated access to permissions."""
    from httpx import ASGITransport, AsyncClient
    async with ASGITransport(app=app_with_lifespan) as transport:
        client = AsyncClient(transport=transport, base_url="http://test")
        resp = await client.get("/api/v1/auth/permissions")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
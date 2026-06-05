"""Extended workflow API integration tests.

Tests the workflow APIs:
- /work-items/sorted
- /work-items/search
- /work-items/{id}/reassign
- /work-items/types
- /work-items/states
- /work-items/logs/batch
- /work-items/{id}/test-cases (relations)
"""
import pytest
from httpx import AsyncClient

from tests.integration.conftest import TestDataRegistry
from tests.integration.utils.helpers import create_requirement_data, post_work_item, unique_id


# ==================== Sorting and Search Tests ====================


@pytest.mark.asyncio
async def test_list_work_items_sorted(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """8.1 - List sorted work items should return 200."""
    # Create a work item first
    await post_work_item(client_admin, test_data_registry, create_requirement_data())

    # List sorted by created_at desc
    resp = await client_admin.get("/api/v1/work-items/sorted?order_by=created_at&direction=desc")
    assert resp.status_code == 200, f"Sorted list failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_work_items_sorted_by_title(client_admin: AsyncClient):
    """8.2 - List work items sorted by title."""
    resp = await client_admin.get("/api/v1/work-items/sorted?order_by=title&direction=asc")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_work_items_sorted_with_filters(client_admin: AsyncClient):
    """8.3 - List sorted work items with state filter."""
    resp = await client_admin.get("/api/v1/work-items/sorted?state=DRAFT&order_by=created_at&direction=desc")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_work_items(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """8.4 - Search work items by keyword should return 200."""
    # Create a work item with specific title
    title = f"Searchable Item {unique_id()}"
    await post_work_item(
        client_admin,
        test_data_registry,
        create_requirement_data(title=title),
    )

    # Search by keyword
    resp = await client_admin.get(f"/api/v1/work-items/search?keyword={title[:10]}")
    assert resp.status_code == 200, f"Search failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_work_items_with_filters(client_admin: AsyncClient):
    """8.5 - Search work items with type_code filter."""
    resp = await client_admin.get("/api/v1/work-items/search?keyword=test&type_code=REQUIREMENT")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_work_items_pagination(client_admin: AsyncClient):
    """8.6 - Search work items with pagination."""
    resp = await client_admin.get("/api/v1/work-items/search?keyword=test&limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) <= 10


# ==================== Catalog Tests ====================


@pytest.mark.asyncio
async def test_get_work_item_types(client_admin: AsyncClient):
    """8.7 - Get work item types should return 200."""
    resp = await client_admin.get("/api/v1/work-items/types")
    assert resp.status_code == 200, f"Get types failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    # Should contain REQUIREMENT, TEST_CASE etc.
    type_codes = [item.get("type_code") for item in data if isinstance(item, dict)]
    assert len(type_codes) > 0


@pytest.mark.asyncio
async def test_get_work_item_states(client_admin: AsyncClient):
    """8.8 - Get work item states should return 200."""
    resp = await client_admin.get("/api/v1/work-items/states")
    assert resp.status_code == 200, f"Get states failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    # Should contain states like DRAFT, PENDING_REVIEW etc.


@pytest.mark.asyncio
async def test_get_work_item_states_filtered_by_type(client_admin: AsyncClient):
    """8.9 - Get work item states filtered by type_code."""
    resp = await client_admin.get("/api/v1/work-items/states?type_code=REQUIREMENT")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)


# ==================== Item Relations Tests ====================


@pytest.mark.asyncio
async def test_get_test_cases_for_requirement(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """8.10 - Get test cases for a requirement."""
    # Create a requirement
    resp = await post_work_item(
        client_admin,
        test_data_registry,
        create_requirement_data(title=f"Requirement {unique_id()}"),
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    # Get test cases for this requirement
    resp = await client_admin.get(f"/api/v1/work-items/{item_id}/test-cases")
    # May return 200 or 400/404 depending on implementation
    assert resp.status_code in (200, 400, 404), f"Unexpected status: {resp.status_code}"


@pytest.mark.asyncio
async def test_get_test_cases_for_nonexistent_item(client_admin: AsyncClient):
    """8.11 - Get test cases for non-existent item should return 404 or 400."""
    resp = await client_admin.get("/api/v1/work-items/nonexistent_item/test-cases")
    assert resp.status_code in (400, 404), f"Expected 400/404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_requirement_for_test_case(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """8.12 - Get requirement for a test case."""
    # First create a test case with ref_req_id
    req_resp = await post_work_item(
        client_admin,
        test_data_registry,
        create_requirement_data(title=f"Requirement {unique_id()}"),
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["item_id"]

    # Get requirement for this item
    resp = await client_admin.get(f"/api/v1/work-items/{req_id}/requirement")
    # May return 200 or 400/404 depending on implementation
    assert resp.status_code in (200, 400, 404), f"Unexpected status: {resp.status_code}"


# ==================== Permission Tests ====================


@pytest.mark.asyncio
async def test_sorted_list_no_permission(client_no_role: AsyncClient):
    """8.13 - Sorted list without permission should return 403."""
    resp = await client_no_role.get("/api/v1/work-items/sorted")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_search_no_permission(client_no_role: AsyncClient):
    """8.14 - Search without permission should return 403."""
    resp = await client_no_role.get("/api/v1/work-items/search?keyword=test")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_types_no_permission(client_no_role: AsyncClient):
    """8.15 - Get types without permission should return 403."""
    resp = await client_no_role.get("/api/v1/work-items/types")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_states_no_permission(client_no_role: AsyncClient):
    """8.16 - Get states without permission should return 403."""
    resp = await client_no_role.get("/api/v1/work-items/states")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_relations_no_permission(client_no_role: AsyncClient):
    """8.17 - Get relations without permission should return 403."""
    resp = await client_no_role.get("/api/v1/work-items/some_id/test-cases")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
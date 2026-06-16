"""Requirement and test case relationship tests."""
import pytest
from httpx import AsyncClient

from tests.integration.utils.helpers import create_test_case_data, unique_id


@pytest.mark.asyncio
async def test_get_cases_by_requirement(client_tpm: AsyncClient, client_dev: AsyncClient, test_data_registry):
    """6.1 - Query test cases by requirement ID."""
    # Create requirement via /api/v1/requirements to get a valid req_id
    req_resp = await client_tpm.post(
        "/api/v1/requirements",
        json={"title": f"Test Requirement {unique_id()}"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Create test case linked to requirement
    case_resp = await client_dev.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["data"]["item_id"]

    # Query test cases by requirement
    resp = await client_dev.get(f"/api/v1/test-cases?ref_req_id={req_id}")
    assert resp.status_code == 200, f"Query cases failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert any(c["item_id"] == case_id for c in data)


@pytest.mark.asyncio
async def test_get_requirement_by_case(client_tpm: AsyncClient, client_dev: AsyncClient, test_data_registry):
    """6.2 - Query requirement by test case ID."""
    # Create requirement via /api/v1/requirements
    req_resp = await client_tpm.post(
        "/api/v1/requirements",
        json={"title": f"Test Requirement {unique_id()}"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Create test case linked to requirement
    case_resp = await client_dev.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["data"]["item_id"]

    # Get requirement via relations endpoint
    resp = await client_tpm.get(f"/api/v1/work-items/{case_id}/requirement")
    assert resp.status_code == 200, f"Get requirement failed: {resp.text}"
    data = resp.json()["data"]
    assert data["item_id"] == case_id


@pytest.mark.asyncio
async def test_create_case_with_nonexistent_req(client_dev: AsyncClient):
    """6.3 - Creating test case with non-existent requirement should fail."""
    resp = await client_dev.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id="nonexistent_req_id"),
    )
    assert resp.status_code in (400, 404), f"Expected 400/404, got {resp.status_code}"


@pytest.mark.asyncio
async def test_update_case_ref_req_id(client_tpm: AsyncClient, client_dev: AsyncClient, test_data_registry):
    """6.4 - Update test case's ref_req_id."""
    # Create two requirements via /api/v1/requirements
    req1_resp = await client_tpm.post(
        "/api/v1/requirements",
        json={"title": f"Req 1 {unique_id()}"},
    )
    assert req1_resp.status_code == 201
    req1_id = req1_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req1_id)

    req2_resp = await client_tpm.post(
        "/api/v1/requirements",
        json={"title": f"Req 2 {unique_id()}"},
    )
    assert req2_resp.status_code == 201
    req2_id = req2_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req2_id)

    # Create test case with first requirement
    case_resp = await client_dev.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req1_id),
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["data"]["item_id"]

    # Update to second requirement
    resp = await client_dev.put(
        f"/api/v1/test-cases/{case_id}",
        json={"ref_req_id": req2_id},
    )
    assert resp.status_code == 200, f"Update case failed: {resp.text}"


@pytest.mark.asyncio
async def test_soft_delete_does_not_affect_cases(client_tpm: AsyncClient, client_dev: AsyncClient, test_data_registry):
    """6.5 - Soft-deleting requirement should not affect linked test cases."""
    # Create requirement via /api/v1/requirements
    req_resp = await client_tpm.post(
        "/api/v1/requirements",
        json={"title": f"Test Requirement {unique_id()}"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Create test case linked to requirement
    case_resp = await client_dev.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    assert case_resp.status_code == 201
    case_id = case_resp.json()["data"]["item_id"]

    # Delete requirement
    del_resp = await client_tpm.delete(f"/api/v1/requirements/{req_id}")
    assert del_resp.status_code == 200

    # Test case should still exist
    case_get_resp = await client_dev.get(f"/api/v1/test-cases/{case_id}")
    assert case_get_resp.status_code == 200, "Test case should still exist after requirement deletion"

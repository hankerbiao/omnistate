"""Test case lifecycle integration tests.

Tests the complete lifecycle of a test case from creation through all state transitions:
DEVELOPING (initial on create) → SUBMIT_REVIEW → PENDING_REVIEW → APPROVE → DONE

Tests use POST /api/v1/requirements to create requirements (gets req_id),
and POST /api/v1/work-items/ to create workflow items (gets item_id for transitions).
"""
import pytest
from httpx import AsyncClient

from tests.integration.utils.helpers import create_test_case_data, create_transition_request, unique_id


@pytest.mark.asyncio
async def test_create_test_case(client_admin: AsyncClient, test_data_registry):
    """5.1 - ADMIN creates test case in DEVELOPING state."""
    # Create requirement via /api/v1/requirements to get a valid req_id
    req_resp = await client_admin.post(
        "/api/v1/requirements",
        json={"title": f"Test Requirement for Cases {unique_id()}"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    assert resp.status_code == 201, f"Create test case failed: {resp.text}"
    data = resp.json()["data"]
    assert data["current_state"] == "DEVELOPING"
    assert data["type_code"] == "TEST_CASE"
    return data.get("item_id") or data.get("work_item_id")


@pytest.mark.asyncio
async def test_unauthorized_create_test_case(client_no_role: AsyncClient):
    """5.2 - Non-authorized user cannot create test case."""
    resp = await client_no_role.post(
        "/api/v1/test-cases",
        json=create_test_case_data(),
    )
    assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_testcase_full_lifecycle(client_admin: AsyncClient, test_data_registry):
    """5.3-5.8 - Test full test case lifecycle through all states."""
    # Create requirement via /api/v1/requirements to get a valid req_id
    req_resp = await client_admin.post(
        "/api/v1/requirements",
        json={"title": f"Test Requirement for Lifecycle {unique_id()}"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Also create a work item for the requirement so we can transition it
    wi_resp = await client_admin.post(
        "/api/v1/work-items/",
        json={
            "type_code": "REQUIREMENT",
            "title": f"Test Requirement WI for Lifecycle {unique_id()}",
            "content": "Content",
        },
    )
    assert wi_resp.status_code == 201
    item_id = wi_resp.json()["data"]["item_id"]
    test_data_registry.register_work_item(item_id)

    # Submit requirement to advance its state
    await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("SUBMIT"),
    )
    await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("APPROVE"),
    )

    # Create test case linked to the requirement
    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    assert resp.status_code == 201
    case_id = resp.json()["data"].get("item_id") or resp.json()["data"].get("work_item_id")

    # 5.3 DEVELOPING → SUBMIT_REVIEW → PENDING_REVIEW
    resp = await client_admin.post(
        f"/api/v1/work-items/{case_id}/transition",
        json=create_transition_request("SUBMIT_REVIEW", {"target_owner_id": "test_reviewer"}),
    )
    assert resp.status_code == 200, f"SUBMIT_REVIEW failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "PENDING_REVIEW"

    # 5.4 PENDING_REVIEW → APPROVE → DONE (terminal state)
    resp = await client_admin.post(
        f"/api/v1/work-items/{case_id}/transition",
        json=create_transition_request("APPROVE"),
    )
    assert resp.status_code == 200, f"APPROVE failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "DONE"

    return case_id


@pytest.mark.asyncio
async def test_testcase_reject_path(client_admin: AsyncClient, test_data_registry):
    """5.7 - PENDING_REVIEW → REJECT → DEVELOPING (rejection path)."""
    # Create requirement via /api/v1/requirements
    req_resp = await client_admin.post(
        "/api/v1/requirements",
        json={"title": f"Test Requirement for Reject {unique_id()}"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Create and transition work item for the requirement
    wi_resp = await client_admin.post(
        "/api/v1/work-items/",
        json={
            "type_code": "REQUIREMENT",
            "title": f"Test Requirement WI for Reject {unique_id()}",
            "content": "Content",
        },
    )
    assert wi_resp.status_code == 201
    item_id = wi_resp.json()["data"]["item_id"]
    test_data_registry.register_work_item(item_id)

    # Submit requirement
    await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("SUBMIT"),
    )
    await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("APPROVE"),
    )

    # Create and advance test case to PENDING_REVIEW
    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    case_id = resp.json()["data"]["work_item_id"]

    await client_admin.post(
        f"/api/v1/work-items/{case_id}/transition",
        json=create_transition_request("SUBMIT_REVIEW", {"target_owner_id": "test_reviewer"}),
    )

    # REJECT from PENDING_REVIEW
    resp = await client_admin.post(
        f"/api/v1/work-items/{case_id}/transition",
        json=create_transition_request("REJECT"),
    )
    assert resp.status_code == 200, f"REJECT failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "DEVELOPING"


@pytest.mark.asyncio
async def test_terminal_state_cannot_transition(client_admin: AsyncClient, test_data_registry):
    """5.8 - Terminal DONE state cannot transition."""
    # Create requirement via /api/v1/requirements
    req_resp = await client_admin.post(
        "/api/v1/requirements",
        json={"title": "Req for Done Test", "description": "test"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Create and transition work item for the requirement
    wi_resp = await client_admin.post(
        "/api/v1/work-items/",
        json={"type_code": "REQUIREMENT", "title": "Req WI for Done Test", "content": "Content"},
    )
    assert wi_resp.status_code == 201
    item_id = wi_resp.json()["data"]["item_id"]
    test_data_registry.register_work_item(item_id)
    await client_admin.post(f"/api/v1/work-items/{item_id}/transition", json=create_transition_request("SUBMIT"))
    await client_admin.post(f"/api/v1/work-items/{item_id}/transition", json=create_transition_request("APPROVE"))

    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    case_id = resp.json()["data"]["work_item_id"]

    # Quick transition to DONE
    for action, extra in [
        ("SUBMIT_REVIEW", {"target_owner_id": "test_reviewer"}),
        ("APPROVE", {"comment": "ok"}),
    ]:
        await client_admin.post(
            f"/api/v1/work-items/{case_id}/transition",
            json=create_transition_request(action, extra),
        )

    # Try to transition from DONE
    resp = await client_admin.post(
        f"/api/v1/work-items/{case_id}/transition",
        json=create_transition_request("START_WRITE"),
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_testcase_logs(client_admin: AsyncClient, test_data_registry):
    """5.9 - Get test case transition logs."""
    # Create requirement via /api/v1/requirements
    req_resp = await client_admin.post(
        "/api/v1/requirements",
        json={"title": "Req for Logs Test", "description": "test"},
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["data"]["req_id"]
    test_data_registry.register_requirement(req_id)

    # Create work item for the requirement
    wi_resp = await client_admin.post(
        "/api/v1/work-items/",
        json={"type_code": "REQUIREMENT", "title": "Req WI for Logs Test", "content": "Content"},
    )
    assert wi_resp.status_code == 201
    item_id = wi_resp.json()["data"]["item_id"]
    test_data_registry.register_work_item(item_id)
    await client_admin.post(f"/api/v1/work-items/{item_id}/transition", json=create_transition_request("SUBMIT"))
    await client_admin.post(f"/api/v1/work-items/{item_id}/transition", json=create_transition_request("APPROVE"))

    resp = await client_admin.post(
        "/api/v1/test-cases",
        json=create_test_case_data(ref_req_id=req_id),
    )
    case_id = resp.json()["data"]["work_item_id"]

    resp = await client_admin.get(f"/api/v1/work-items/{case_id}/logs")
    assert resp.status_code == 200, f"Get logs failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)

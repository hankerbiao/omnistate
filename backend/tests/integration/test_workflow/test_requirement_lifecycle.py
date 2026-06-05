"""Requirement lifecycle integration tests.

Tests the complete lifecycle of a requirement from creation through all state transitions:
DRAFT → SUBMIT → PENDING_REVIEW → APPROVE → PENDING_DEVELOP
→ START → DEVELOPING → FINISH → PENDING_TEST → PASS → PENDING_UAT
→ PASS → PENDING_RELEASE → PUBLISH → RELEASED
"""
import pytest
from httpx import AsyncClient

from tests.integration.conftest import TestDataRegistry
from tests.integration.utils.helpers import (
    create_requirement_data,
    create_transition_request,
    post_work_item,
    unique_id,
)


@pytest.mark.asyncio
async def test_tpm_create_requirement(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """4.1 - ADMIN/TPM creates requirement in DRAFT state."""
    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201, f"Create requirement failed: {resp.text}"
    data = resp.json()["data"]
    assert data["current_state"] == "DRAFT"
    assert data["type_code"] == "REQUIREMENT"
    return data["item_id"]


@pytest.mark.asyncio
async def test_non_tpm_create_requirement_forbidden(client_no_role: AsyncClient):
    """4.2 - User without work_items:write cannot create requirement."""
    resp = await client_no_role.post(
        "/api/v1/work-items/",
        json=create_requirement_data(),
    )
    assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_requirement_full_lifecycle(
    client_admin: AsyncClient,
    client_reviewer: AsyncClient,
    client_dev: AsyncClient,
    client_qa: AsyncClient,
    client_tpm: AsyncClient,
    test_users: dict,
    test_data_registry: TestDataRegistry,
):
    """4.3-4.11 - Test full requirement lifecycle through all states."""
    reviewer_id = test_users["REVIEWER"]["user_id"]
    dev_id = test_users["MANUAL_DEV"]["user_id"]
    qa_id = test_users["QA"]["user_id"]
    tpm_id = test_users["TPM"]["user_id"]

    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    # 4.3 DRAFT → SUBMIT → PENDING_REVIEW（创建人提交，指派审核人）
    resp = await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request(
            "SUBMIT",
            {"target_owner_id": reviewer_id, "priority": "HIGH"},
        ),
    )
    assert resp.status_code == 200, f"SUBMIT failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "PENDING_REVIEW"

    # 4.4 PENDING_REVIEW → APPROVE → PENDING_DEVELOP（当前负责人审核）
    resp = await client_reviewer.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request(
            "APPROVE",
            {"target_owner_id": dev_id, "comment": "approved"},
        ),
    )
    assert resp.status_code == 200, f"APPROVE failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "PENDING_DEVELOP"

    # 4.6 PENDING_DEVELOP → START → DEVELOPING
    resp = await client_dev.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("START"),
    )
    assert resp.status_code == 200, f"START failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "DEVELOPING"

    # 4.7 DEVELOPING → FINISH → PENDING_TEST
    resp = await client_dev.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("FINISH", {"target_owner_id": qa_id}),
    )
    assert resp.status_code == 200, f"FINISH failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "PENDING_TEST"

    # 4.8 PENDING_TEST → PASS → PENDING_UAT
    resp = await client_qa.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("PASS", {"target_owner_id": tpm_id}),
    )
    assert resp.status_code == 200, f"PASS failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "PENDING_UAT"

    # 4.10 PENDING_UAT → PASS → PENDING_RELEASE
    resp = await client_tpm.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("PASS", {"target_owner_id": tpm_id}),
    )
    assert resp.status_code == 200, f"UAT PASS failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "PENDING_RELEASE"

    # 4.11 PENDING_RELEASE → PUBLISH → RELEASED
    resp = await client_tpm.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("PUBLISH"),
    )
    assert resp.status_code == 200, f"PUBLISH failed: {resp.text}"
    assert resp.json()["data"]["to_state"] == "RELEASED"

    return item_id


@pytest.mark.asyncio
async def test_admin_cannot_approve_when_not_owner(
    client_admin: AsyncClient,
    client_reviewer: AsyncClient,
    test_users: dict,
    test_data_registry: TestDataRegistry,
):
    """Admin 创建并提交后，若待办在审核人处，admin 不能代审。"""
    reviewer_id = test_users["REVIEWER"]["user_id"]

    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    resp = await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request(
            "SUBMIT",
            {"target_owner_id": reviewer_id, "priority": "HIGH"},
        ),
    )
    assert resp.status_code == 200

    resp = await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request(
            "APPROVE",
            {"target_owner_id": reviewer_id, "comment": "should fail"},
        ),
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_terminal_state_cannot_transition(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """4.12 - Terminal state cannot transition."""
    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    # Transition to RELEASED quickly（全程保持 test_admin 为 current_owner）
    transition_data = {
        "SUBMIT": {"target_owner_id": "test_admin", "priority": "HIGH"},
        "APPROVE": {"target_owner_id": "test_admin", "comment": "ok"},
        "START": {},
        "FINISH": {"target_owner_id": "test_admin"},
        "PASS": {"target_owner_id": "test_admin"},
        "PUBLISH": {},
    }
    for action in ["SUBMIT", "APPROVE", "START", "FINISH", "PASS", "PASS", "PUBLISH"]:
        resp = await client_admin.post(
            f"/api/v1/work-items/{item_id}/transition",
            json=create_transition_request(action, transition_data.get(action, {})),
        )
        if resp.status_code != 200:
            break

    # Try to transition from RELEASED
    resp = await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("SUBMIT"),
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"


@pytest.mark.asyncio
async def test_unauthorized_transition(
    client_admin: AsyncClient,
    client_no_role: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """4.13 - Unauthorized role cannot perform transition."""
    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    # Submit first（指派他人为当前负责人）
    await client_admin.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request(
            "SUBMIT",
            {"target_owner_id": "some_reviewer", "priority": "HIGH"},
        ),
    )

    # No role user tries to APPROVE (should be denied)
    resp = await client_no_role.post(
        f"/api/v1/work-items/{item_id}/transition",
        json=create_transition_request("APPROVE"),
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_transition_logs(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """4.14 - Get transition logs should return 200."""
    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    resp = await client_admin.get(f"/api/v1/work-items/{item_id}/logs")
    assert resp.status_code == 200, f"Get logs failed: {resp.text}"
    data = resp.json()["data"]
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_available_transitions(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """4.15 - Get available transitions should return 200."""
    resp = await post_work_item(
        client_admin,
        test_data_registry,
        create_requirement_data(title=f"Test Transitions {unique_id()}"),
    )
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    item_id = resp.json()["data"]["item_id"]

    resp = await client_admin.get(f"/api/v1/work-items/{item_id}/transitions")
    assert resp.status_code == 200, f"Get transitions failed: {resp.text}"
    data = resp.json()["data"]
    assert "available_transitions" in data


@pytest.mark.asyncio
async def test_delete_requirement(
    client_admin: AsyncClient,
    test_data_registry: TestDataRegistry,
):
    """4.16 - Delete requirement should return 200."""
    resp = await post_work_item(
        client_admin, test_data_registry, create_requirement_data()
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["item_id"]

    resp = await client_admin.delete(f"/api/v1/work-items/{item_id}")
    assert resp.status_code == 200, f"Delete failed: {resp.text}"

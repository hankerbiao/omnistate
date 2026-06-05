"""Test data factory functions.

Provides utilities for generating test data with unique identifiers.
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tests.integration.conftest import TestDataRegistry


def timestamp() -> int:
    """Current timestamp for unique identifiers."""
    return int(time.time())


def unique_id(prefix: str = "test") -> str:
    """Generate unique ID for test data."""
    return f"{prefix}_{time.time_ns()}"


def create_requirement_data(title: str | None = None, content: str | None = None) -> dict[str, Any]:
    """Create test requirement data."""
    return {
        "type_code": "REQUIREMENT",
        "title": title or f"Test Requirement {unique_id()}",
        "content": content or f"Test requirement content for {unique_id()}",
    }


# Matches scripts/migrate_test_case_catalog.py DEFAULT_LAB_ID; run migration before integration tests.
DEFAULT_INTEGRATION_LAB_ID = "LAB-DEFAULT"


def create_test_case_data(
    ref_req_id: str | None = None,
    title: str | None = None,
    priority: str = "MEDIUM",
    lab_id: str | None = None,
    catalog_path: list[str] | None = None,
    **extra_fields,
) -> dict[str, Any]:
    """Create test case payload; lab_id must exist (default lab from migration script)."""
    if not lab_id:
        lab_id = DEFAULT_INTEGRATION_LAB_ID
    data: dict[str, Any] = {
        "title": title or f"Test Case {unique_id()}",
        "priority": priority,
        "lab_id": lab_id,
        "catalog_path": catalog_path or ["integration"],
    }
    if ref_req_id:
        data["ref_req_id"] = ref_req_id
    # Allow passing extra fields that will be set conditionally
    for key, value in extra_fields.items():
        if value is not None:
            data[key] = value
    return data


def create_user_data(user_id: str | None = None, role_ids: list[str] | None = None) -> dict[str, Any]:
    """Create user data for testing."""
    uid = user_id or unique_id("user")
    return {
        "user_id": uid,
        "username": f"User {uid}",
        "password": "Test@123",
        "email": f"{uid}@test.local",
        "role_ids": role_ids or [],
    }


def create_role_data(role_id: str | None = None, name: str | None = None) -> dict[str, Any]:
    """Create role data for testing."""
    rid = role_id or unique_id("role")
    return {
        "role_id": rid,
        "name": name or f"Role {rid}",
        "description": f"Test role {rid}",
        "permission_ids": [],
    }


def create_permission_data(perm_id: str | None = None, code: str | None = None) -> dict[str, Any]:
    """Create permission payload for integration tests."""
    pid = perm_id or unique_id("test_perm")
    return {
        "perm_id": pid,
        "code": code or f"test.code.{unique_id()}",
        "name": f"Test Permission {pid}",
        "description": "Test permission description",
    }


def create_transition_request(action: str, form_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create transition request data."""
    return {
        "action": action,
        "form_data": form_data or {},
    }


def register_created_lab(registry: "TestDataRegistry", lab_data: dict[str, Any]) -> None:
    """Track a lab created during an integration test for teardown cleanup."""
    lab_id = lab_data.get("lab_id")
    if lab_id:
        registry.register_lab(lab_id)


def register_created_work_item(registry: "TestDataRegistry", data: dict[str, Any]) -> None:
    """Track a work item (and linked req_id if present) for teardown cleanup."""
    item_id = data.get("item_id") or data.get("id")
    if item_id:
        registry.register_work_item(str(item_id))
    req_id = data.get("req_id")
    if req_id:
        registry.register_requirement(req_id)


def register_created_requirement(registry: "TestDataRegistry", data: dict[str, Any]) -> None:
    """Track a test requirement (and linked work item) for teardown cleanup."""
    req_id = data.get("req_id")
    if req_id:
        registry.register_requirement(req_id)
    workflow_item_id = data.get("workflow_item_id")
    if workflow_item_id:
        registry.register_work_item(str(workflow_item_id))


def register_created_test_case(registry: "TestDataRegistry", data: dict[str, Any]) -> None:
    """Track a test case for teardown cleanup."""
    case_id = data.get("case_id")
    if case_id:
        registry.register_test_case(case_id)


def register_created_role(registry: "TestDataRegistry", data: dict[str, Any]) -> None:
    """Track a role created during an integration test for teardown cleanup."""
    role_id = data.get("role_id")
    if role_id:
        registry.register_role(role_id)


async def post_work_item(
    client: Any,
    registry: "TestDataRegistry | None",
    payload: dict[str, Any],
) -> Any:
    """POST /work-items/ and register created item for teardown cleanup."""
    resp = await client.post("/api/v1/work-items/", json=payload)
    if registry is not None and resp.status_code == 201:
        register_created_work_item(registry, resp.json()["data"])
    return resp


async def post_requirement(
    client: Any,
    registry: "TestDataRegistry | None",
    payload: dict[str, Any],
) -> Any:
    """POST /requirements and register created requirement for teardown cleanup."""
    resp = await client.post("/api/v1/requirements", json=payload)
    if registry is not None and resp.status_code == 201:
        register_created_requirement(registry, resp.json()["data"])
    return resp


async def delete_catalog_lab(client: Any, lab_id: str) -> None:
    """Best-effort delete of a catalog lab (204/404 acceptable)."""
    resp = await client.delete(f"/api/v1/catalog/labs/{lab_id}")
    assert resp.status_code in (204, 404), (
        f"Cleanup catalog lab failed: {resp.status_code} {resp.text}"
    )

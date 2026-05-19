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
    return f"{prefix}_{timestamp()}"


def create_requirement_data(title: str | None = None, content: str | None = None) -> dict[str, Any]:
    """Create test requirement data."""
    return {
        "type_code": "REQUIREMENT",
        "title": title or f"Test Requirement {unique_id()}",
        "content": content or f"Test requirement content for {unique_id()}",
    }


def create_test_case_data(
    ref_req_id: str | None = None,
    title: str | None = None,
    priority: str = "MEDIUM",
    **extra_fields,
) -> dict[str, Any]:
    """Create test case data.

    Note: ref_req_id is required in CreateTestCaseRequest.
    If not provided, caller should set it to a valid req_id.
    """
    data: dict[str, Any] = {
        "title": title or f"Test Case {unique_id()}",
        "priority": priority,
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


def create_transition_request(action: str, form_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create transition request data."""
    return {
        "action": action,
        "form_data": form_data or {},
    }
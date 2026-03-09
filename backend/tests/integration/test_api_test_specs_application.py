from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.modules.test_specs.api import test_case_routes, test_required_routes
from app.shared.auth import jwt_auth


def _requirement_response(owner_id: str) -> dict:
    now = datetime(2024, 1, 1).isoformat()
    return {
        "id": "req-1",
        "req_id": "REQ-1",
        "workflow_item_id": "workflow-1",
        "title": "Requirement A",
        "description": "desc",
        "technical_spec": None,
        "target_components": [],
        "firmware_version": None,
        "priority": "P1",
        "key_parameters": [],
        "risk_points": None,
        "tpm_owner_id": owner_id,
        "manual_dev_id": None,
        "auto_dev_id": None,
        "status": "DRAFT",
        "attachments": [],
        "created_at": now,
        "updated_at": now,
    }


def _test_case_response(owner_id: str) -> dict:
    now = datetime(2024, 1, 1).isoformat()
    return {
        "id": "case-1",
        "case_id": "TC-1",
        "ref_req_id": "REQ-1",
        "workflow_item_id": "workflow-1",
        "title": "Case A",
        "version": 1,
        "is_active": True,
        "change_log": None,
        "status": "DRAFT",
        "owner_id": owner_id,
        "reviewer_id": None,
        "auto_dev_id": None,
        "priority": None,
        "estimated_duration_sec": None,
        "target_components": [],
        "required_env": {},
        "tags": [],
        "test_category": None,
        "tooling_req": [],
        "is_destructive": False,
        "pre_condition": None,
        "post_condition": None,
        "cleanup_steps": [],
        "steps": [],
        "is_need_auto": False,
        "is_automated": False,
        "automation_type": None,
        "script_entity_id": None,
        "automation_case_ref": None,
        "risk_level": None,
        "failure_analysis": None,
        "confidentiality": None,
        "visibility_scope": None,
        "attachments": [],
        "custom_fields": {},
        "deprecation_reason": None,
        "approval_history": [],
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture()
def app(app, monkeypatch):
    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return [
            "requirements:write",
            "test_cases:write",
        ]

    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_requirement_create_route_delegates_to_command_service(app):
    client = TestClient(app)

    class FakeRequirementCommandService:
        async def create_requirement(self, context, command):
            assert context.actor_id == "test-user"
            assert command.payload["title"] == "Requirement A"
            return _requirement_response(owner_id=context.actor_id)

    app.dependency_overrides[test_required_routes.get_requirement_command_service] = (
        lambda: FakeRequirementCommandService()
    )

    response = client.post(
        "/api/v1/requirements",
        json={"title": "Requirement A"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["tpm_owner_id"] == "test-user"


def test_test_case_create_route_delegates_to_command_service(app):
    client = TestClient(app)

    class FakeTestCaseCommandService:
        async def create_test_case(self, context, command):
            assert context.actor_id == "test-user"
            assert command.payload["title"] == "Case A"
            assert command.payload["ref_req_id"] == "REQ-1"
            return _test_case_response(owner_id=context.actor_id)

    app.dependency_overrides[test_case_routes.get_test_case_command_service] = (
        lambda: FakeTestCaseCommandService()
    )

    response = client.post(
        "/api/v1/test-cases",
        json={"title": "Case A", "ref_req_id": "REQ-1"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["owner_id"] == "test-user"

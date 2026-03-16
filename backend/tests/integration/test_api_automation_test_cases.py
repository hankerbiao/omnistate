from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.modules.test_specs.api import automation_test_case_routes
from app.shared.auth import jwt_auth


def _automation_test_case_response() -> dict:
    now = datetime(2024, 1, 1).isoformat()
    return {
        "id": "auto-case-1",
        "auto_case_id": "ATC-2026-00001",
        "name": "Login API Smoke",
        "version": "1.0.0",
        "status": "ACTIVE",
        "framework": "pytest",
        "automation_type": "API",
        "repo_url": "https://git.example.com/qa/auto-tests",
        "repo_branch": "main",
        "script_entity_id": "script-1",
        "entry_command": "pytest tests/login/test_smoke.py",
        "runtime_env": {"python": "3.13"},
        "tags": ["smoke", "login"],
        "maintainer_id": "test-user",
        "reviewer_id": "reviewer-1",
        "description": "Login smoke automation case",
        "assertions": ["status_code == 200"],
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture()
def app(app, monkeypatch):
    class FakeAutomationTestCaseService:
        async def create_automation_test_case(self, payload):
            assert payload["name"] == "Login API Smoke"
            return _automation_test_case_response()

        async def list_automation_test_cases(
            self,
            framework=None,
            automation_type=None,
            status=None,
            maintainer_id=None,
            limit=20,
            offset=0,
        ):
            item = _automation_test_case_response()
            item["framework"] = framework or item["framework"]
            item["automation_type"] = automation_type or item["automation_type"]
            item["status"] = status or item["status"]
            item["maintainer_id"] = maintainer_id or item["maintainer_id"]
            return [item]

        async def get_automation_test_case(self, auto_case_id):
            item = _automation_test_case_response()
            item["auto_case_id"] = auto_case_id
            return item

    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return [
            "test_cases:write",
            "test_cases:read",
        ]

    app.dependency_overrides[automation_test_case_routes.get_automation_test_case_service] = (
        lambda: FakeAutomationTestCaseService()
    )
    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_create_automation_test_case_route(client):
    response = client.post(
        "/api/v1/automation-test-cases",
        json={
            "name": "Login API Smoke",
            "framework": "pytest",
            "automation_type": "API",
            "repo_url": "https://git.example.com/qa/auto-tests",
            "entry_command": "pytest tests/login/test_smoke.py",
            "runtime_env": {"python": "3.13"},
            "tags": ["smoke", "login"],
            "assertions": ["status_code == 200"],
        },
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["auto_case_id"] == "ATC-2026-00001"
    assert payload["data"]["name"] == "Login API Smoke"
    assert payload["data"]["framework"] == "pytest"


def test_list_automation_test_cases_route(client):
    response = client.get(
        "/api/v1/automation-test-cases?framework=pytest&automation_type=API&status=ACTIVE",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert len(payload["data"]) == 1
    assert payload["data"][0]["framework"] == "pytest"
    assert payload["data"][0]["automation_type"] == "API"


def test_get_automation_test_case_route(client):
    response = client.get(
        "/api/v1/automation-test-cases/ATC-2026-00999",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["auto_case_id"] == "ATC-2026-00999"

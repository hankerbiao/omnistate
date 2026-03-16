from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.execution.api import routes as execution_routes
from app.shared.auth import jwt_auth


@pytest.fixture()
def app(app, monkeypatch):
    class FakeExecutionService:
        async def cancel_scheduled_task(self, task_id, actor_id):
            return {
                "task_id": task_id,
                "schedule_type": "SCHEDULED",
                "schedule_status": "CANCELLED",
                "dispatch_status": "CANCELLED",
                "overall_status": "CANCELLED",
                "planned_at": datetime.now(timezone.utc) + timedelta(hours=1),
                "triggered_at": None,
                "updated_at": datetime.now(timezone.utc),
            }

        async def update_scheduled_task(self, task_id, actor_id, payload):
            return {
                "task_id": task_id,
                "external_task_id": f"EXT-{task_id}",
                "agent_id": payload.get("agent_id", "agent-01"),
                "dispatch_channel": "HTTP",
                "dedup_key": "updated-key",
                "schedule_type": "SCHEDULED",
                "schedule_status": "PENDING",
                "dispatch_status": "PENDING",
                "consume_status": "PENDING",
                "overall_status": "QUEUED",
                "case_count": len(payload.get("cases", [])) or 1,
                "planned_at": payload.get("planned_at", datetime.now(timezone.utc) + timedelta(hours=2)),
                "triggered_at": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return ["execution_tasks:write", "execution_tasks:read"]

    app.dependency_overrides[execution_routes.get_execution_service] = lambda: FakeExecutionService()
    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_cancel_scheduled_task_route(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/execution/tasks/ET-2026-000001/cancel",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["schedule_status"] == "CANCELLED"
    assert payload["data"]["overall_status"] == "CANCELLED"


def test_update_scheduled_task_route(app):
    client = TestClient(app)
    response = client.put(
        "/api/v1/execution/tasks/ET-2026-000001/schedule",
        json={
            "agent_id": "agent-02",
            "planned_at": "2026-03-20T10:00:00Z",
            "cases": [{"case_id": "TC-001"}, {"case_id": "TC-002"}],
        },
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["schedule_status"] == "PENDING"
    assert payload["data"]["agent_id"] == "agent-02"
    assert payload["data"]["case_count"] == 2

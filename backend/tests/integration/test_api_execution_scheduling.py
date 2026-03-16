from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.execution.api import routes as execution_routes
from app.shared.auth import jwt_auth


@pytest.fixture()
def app(app, monkeypatch):
    class FakeExecutionService:
        async def dispatch_execution_task(self, command, actor_id):
            return {
                "task_id": command.task_id,
                "external_task_id": command.external_task_id,
                "agent_id": command.agent_id,
                "dispatch_channel": "HTTP",
                "dedup_key": "abc",
                "schedule_type": command.schedule_type,
                "schedule_status": "PENDING" if command.schedule_type == "SCHEDULED" else "TRIGGERED",
                "dispatch_status": "PENDING" if command.schedule_type == "SCHEDULED" else "DISPATCHED",
                "consume_status": "PENDING",
                "overall_status": "QUEUED",
                "case_count": len(command.case_ids),
                "planned_at": command.planned_at,
                "triggered_at": None if command.schedule_type == "SCHEDULED" else datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "message": "ok",
            }

    class FakeSequenceIdService:
        async def next(self, key, session=None):
            assert key.startswith("execution_task:")
            return 1

    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return ["execution_tasks:write", "execution_tasks:read"]

    app.dependency_overrides[execution_routes.get_execution_service] = lambda: FakeExecutionService()
    app.dependency_overrides[execution_routes.get_sequence_id_service] = lambda: FakeSequenceIdService()
    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_scheduled_dispatch_route_returns_pending_schedule(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/execution/tasks/dispatch",
        json={
            "framework": "pytest",
            "agent_id": "agent-01",
            "schedule_type": "SCHEDULED",
            "planned_at": "2026-03-20T10:00:00Z",
            "cases": [{"case_id": "TC-001"}],
        },
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["schedule_type"] == "SCHEDULED"
    assert payload["data"]["schedule_status"] == "PENDING"

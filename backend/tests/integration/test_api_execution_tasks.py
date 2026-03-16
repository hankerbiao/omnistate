import pytest
from fastapi.testclient import TestClient

from app.modules.execution.api import routes as execution_routes
from app.shared.auth import jwt_auth


@pytest.fixture()
def app(app, monkeypatch):
    class FakeExecutionService:
        async def list_tasks(self, **filters):
            return [
                {
                    "task_id": "ET-2026-000001",
                    "external_task_id": "EXT-ET-2026-000001",
                    "framework": filters.get("framework") or "pytest",
                    "agent_id": filters.get("agent_id") or "agent-01",
                    "dispatch_channel": "HTTP",
                    "dedup_key": "dedup-001",
                    "schedule_type": filters.get("schedule_type") or "SCHEDULED",
                    "schedule_status": filters.get("schedule_status") or "PENDING",
                    "dispatch_status": filters.get("dispatch_status") or "PENDING",
                    "consume_status": filters.get("consume_status") or "PENDING",
                    "overall_status": filters.get("overall_status") or "QUEUED",
                    "case_count": 2,
                    "planned_at": "2026-03-20T10:00:00Z",
                    "triggered_at": None,
                    "created_at": "2026-03-16T00:00:00Z",
                    "updated_at": "2026-03-16T00:00:00Z",
                }
            ]

        async def ack_task_consumed(self, task_id, consumer_id=None):
            return {
                "task_id": task_id,
                "consume_status": "CONSUMED",
                "consumed_at": "2026-03-16T00:00:00Z",
                "consumer_id": consumer_id,
            }

    async def _fake_current_user():
        return {"user_id": "test-user"}

    async def _fake_get_user_permissions(_user_id: str):
        return [
            "execution_tasks:read",
            "execution_tasks:write",
        ]

    app.dependency_overrides[execution_routes.get_execution_service] = lambda: FakeExecutionService()
    app.dependency_overrides[jwt_auth.get_current_user] = _fake_current_user
    monkeypatch.setattr(jwt_auth, "get_user_permissions", _fake_get_user_permissions)
    return app


def test_ack_task_consumed_route(app):
    client = TestClient(app)

    response = client.post(
        "/api/v1/execution/tasks/ET-2026-000001/consume-ack",
        json={"consumer_id": "consumer-1"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == "ET-2026-000001"
    assert payload["data"]["consume_status"] == "CONSUMED"


def test_list_tasks_route(app):
    client = TestClient(app)

    response = client.get(
        "/api/v1/execution/tasks?schedule_status=PENDING&agent_id=agent-01",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert len(payload["data"]) == 1
    assert payload["data"][0]["task_id"] == "ET-2026-000001"
    assert payload["data"][0]["schedule_status"] == "PENDING"

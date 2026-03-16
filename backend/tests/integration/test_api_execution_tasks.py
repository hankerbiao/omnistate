import pytest
from fastapi.testclient import TestClient

from app.modules.execution.api import routes as execution_routes
from app.shared.auth import jwt_auth


@pytest.fixture()
def app(app, monkeypatch):
    class FakeExecutionService:
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

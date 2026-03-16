from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.execution.api import routes as execution_routes


@pytest.fixture()
def app(app):
    class FakeExecutionService:
        async def report_task_event(self, task_id, payload):
            return {
                "task_id": task_id,
                "event_id": payload["event_id"],
                "event_type": payload["event_type"].upper(),
                "seq": payload.get("seq", 0),
                "received_at": datetime(2026, 3, 16, tzinfo=timezone.utc),
                "processed": True,
            }

        async def report_case_status(self, task_id, case_id, payload):
            return {
                "task_id": task_id,
                "case_id": case_id,
                "status": payload["status"].upper(),
                "progress_percent": payload.get("progress_percent"),
                "step_total": payload.get("step_total") or 0,
                "step_passed": payload.get("step_passed") or 0,
                "step_failed": payload.get("step_failed") or 0,
                "step_skipped": payload.get("step_skipped") or 0,
                "last_seq": payload.get("seq", 0),
                "accepted": True,
                "started_at": None,
                "finished_at": None,
                "updated_at": datetime(2026, 3, 16, tzinfo=timezone.utc),
            }

        async def complete_task(self, task_id, payload):
            return {
                "task_id": task_id,
                "overall_status": payload["status"].upper(),
                "dispatch_status": "COMPLETED",
                "consume_status": "CONSUMED",
                "reported_case_count": 2,
                "started_at": datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc),
                "finished_at": datetime(2026, 3, 16, 10, 5, tzinfo=timezone.utc),
                "last_callback_at": datetime(2026, 3, 16, 10, 5, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 3, 16, 10, 5, tzinfo=timezone.utc),
            }

    app.dependency_overrides[execution_routes.get_execution_service] = lambda: FakeExecutionService()
    return app


def test_report_task_event_route(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/execution/tasks/ET-2026-000001/events",
        json={
            "event_id": "evt-1",
            "event_type": "task_started",
            "seq": 1,
            "payload": {"agent_id": "agent-01"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["event_id"] == "evt-1"
    assert payload["data"]["event_type"] == "TASK_STARTED"


def test_report_case_status_route(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/execution/tasks/ET-2026-000001/cases/TC-001/status",
        json={
            "status": "running",
            "seq": 2,
            "progress_percent": 50,
            "step_total": 4,
            "step_passed": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["case_id"] == "TC-001"
    assert payload["data"]["status"] == "RUNNING"
    assert payload["data"]["progress_percent"] == 50


def test_complete_task_route(app):
    client = TestClient(app)
    response = client.post(
        "/api/v1/execution/tasks/ET-2026-000001/complete",
        json={
            "status": "passed",
            "summary": {"passed": 2},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["task_id"] == "ET-2026-000001"
    assert payload["data"]["overall_status"] == "PASSED"

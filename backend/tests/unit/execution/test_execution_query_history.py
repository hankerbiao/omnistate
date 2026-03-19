from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution.application.execution_service import ExecutionService  # noqa: E402


@pytest.mark.asyncio
async def test_list_tasks_includes_case_execution_summary(monkeypatch):
    task_docs = [
        SimpleNamespace(
            task_id="task-1",
            external_task_id="ext-task-1",
            framework="pytest",
            agent_id="agent-1",
            dispatch_channel="KAFKA",
            dedup_key="dedup-1",
            schedule_type="IMMEDIATE",
            schedule_status="TRIGGERED",
            dispatch_status="DISPATCHED",
            consume_status="PENDING",
            overall_status="RUNNING",
            case_count=2,
            current_case_id="case-2",
            current_case_index=1,
            stop_mode="NONE",
            stop_requested_at=None,
            stop_requested_by=None,
            stop_reason=None,
            planned_at=None,
            triggered_at=None,
            created_at=None,
            updated_at=None,
            request_payload={
                "cases": [
                    {"case_id": "case-1", "auto_case_id": "auto-1"},
                    {"case_id": "case-2", "auto_case_id": "auto-2"},
                ]
            },
        )
    ]
    case_docs = [
        SimpleNamespace(
            task_id="task-1",
            case_id="case-1",
            order_no=0,
            case_snapshot={"title": "Case 1", "auto_case_id": "auto-1"},
            status="PASSED",
            progress_percent=100.0,
            dispatch_status="COMPLETED",
            dispatch_attempts=1,
            event_count=3,
            failure_message=None,
            started_at=None,
            finished_at=None,
            last_event_id="evt-1",
            last_event_at=None,
            result_data={"status": "PASSED"},
        ),
        SimpleNamespace(
            task_id="task-1",
            case_id="case-2",
            order_no=1,
            case_snapshot={"title": "Case 2", "auto_case_id": "auto-2"},
            status="RUNNING",
            progress_percent=50.0,
            dispatch_status="DISPATCHED",
            dispatch_attempts=1,
            event_count=2,
            failure_message=None,
            started_at=None,
            finished_at=None,
            last_event_id="evt-2",
            last_event_at=None,
            result_data={},
        ),
    ]

    class FakeTaskQuery:
        def sort(self, *args, **kwargs):
            return self

        def skip(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        async def to_list(self):
            return task_docs

    class FakeCaseQuery:
        def sort(self, *args, **kwargs):
            return self

        async def to_list(self):
            return case_docs

    class FakeExecutionTaskDoc:
        @staticmethod
        def find(query):
            return FakeTaskQuery()

    class FakeExecutionTaskCaseDoc:
        @staticmethod
        def find(query):
            return FakeCaseQuery()

    import app.modules.execution.application.task_query_mixin as query_module

    monkeypatch.setattr(query_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(query_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)

    result = await ExecutionService().list_tasks()

    assert result == [
        {
            "task_id": "task-1",
            "external_task_id": "ext-task-1",
            "framework": "pytest",
            "agent_id": "agent-1",
            "dispatch_channel": "KAFKA",
            "dedup_key": "dedup-1",
            "schedule_type": "IMMEDIATE",
            "schedule_status": "TRIGGERED",
            "dispatch_status": "DISPATCHED",
            "consume_status": "PENDING",
            "overall_status": "RUNNING",
            "case_count": 2,
            "auto_case_ids": ["auto-1", "auto-2"],
            "current_case_id": "case-2",
            "current_auto_case_id": "auto-2",
            "current_case_index": 1,
            "stop_mode": "NONE",
            "stop_requested_at": None,
            "stop_requested_by": None,
            "stop_reason": None,
            "planned_at": None,
            "triggered_at": None,
            "created_at": None,
            "updated_at": None,
            "cases": [
                {
                    "task_id": "task-1",
                    "case_id": "case-1",
                    "auto_case_id": "auto-1",
                    "order_no": 0,
                    "title": "Case 1",
                    "status": "PASSED",
                    "progress_percent": 100.0,
                    "dispatch_status": "COMPLETED",
                    "dispatch_attempts": 1,
                    "event_count": 3,
                    "failure_message": None,
                    "started_at": None,
                    "finished_at": None,
                    "last_event_id": "evt-1",
                    "last_event_at": None,
                    "result_data": {"status": "PASSED"},
                },
                {
                    "task_id": "task-1",
                    "case_id": "case-2",
                    "auto_case_id": "auto-2",
                    "order_no": 1,
                    "title": "Case 2",
                    "status": "RUNNING",
                    "progress_percent": 50.0,
                    "dispatch_status": "DISPATCHED",
                    "dispatch_attempts": 1,
                    "event_count": 2,
                    "failure_message": None,
                    "started_at": None,
                    "finished_at": None,
                    "last_event_id": "evt-2",
                    "last_event_at": None,
                    "result_data": {},
                },
            ],
        }
    ]

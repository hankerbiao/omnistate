from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService  # noqa: E402


@pytest.mark.asyncio
async def test_ingest_task_finish_marks_task_as_passed(monkeypatch):
    service = ExecutionEventIngestService()

    task_doc = SimpleNamespace(
        task_id="task-1",
        case_count=2,
        reported_case_count=1,
        overall_status="RUNNING",
        consume_status="PENDING",
        started_case_count=1,
        finished_case_count=1,
        passed_case_count=1,
        failed_case_count=0,
        progress_percent=50.0,
        last_event_at=None,
        last_event_id=None,
        last_event_type=None,
        last_event_phase=None,
        started_at=None,
        finished_at=None,
        last_callback_at=None,
    )
    task_doc.save = _async_noop

    class FakeExecutionEventDoc:
        @staticmethod
        async def find_one(query):
            return None

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def insert(self):
            return self

    class FakeExecutionTaskDoc:
        @staticmethod
        async def find_one(query):
            return task_doc

    class FakeExecutionTaskCaseDoc:
        @staticmethod
        async def find_one(query):
            return None

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "demo-test-event@1",
            "event_id": "evt-task-finish",
            "task_id": "task-1",
            "timestamp": "2026-03-18T01:20:09.837565+00:00",
            "event_type": "progress",
            "phase": "task_finish",
            "status": "PASSED",
            "total_cases": 2,
            "started_cases": 2,
            "finished_cases": 2,
            "failed_cases": 0,
        },
        metadata={"partition": 0, "offset": 2},
    )

    assert processed is True
    assert task_doc.overall_status == "PASSED"
    assert task_doc.finished_case_count == 2
    assert task_doc.passed_case_count == 2
    assert task_doc.progress_percent == 100.0
    assert task_doc.finished_at is not None


async def _async_noop():
    return None

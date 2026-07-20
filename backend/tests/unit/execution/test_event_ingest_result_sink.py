"""执行事件消费后的计划结果回写测试。"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService


class _AwaitableDoc(SimpleNamespace):
    async def save(self) -> None:
        return None


class _FindOneDoc:
    def __init__(self, doc):
        self._doc = doc

    async def __call__(self, *args, **kwargs):
        return self._doc


async def test_ingest_final_task_event_publishes_result_to_sink() -> None:
    task_doc = _AwaitableDoc(
        task_id="task-1",
        overall_status="RUNNING",
        finished_case_count=0,
        started_case_count=0,
        failed_case_count=0,
        passed_case_count=0,
        reported_case_count=0,
        current_case_id=None,
        current_case_index=0,
        case_count=1,
        progress_percent=None,
        started_at=None,
        finished_at=None,
        last_callback_at=None,
    )
    result_sink = SimpleNamespace(apply_execution_result=AsyncMock())
    service = ExecutionEventIngestService(
        progress_coordinator=SimpleNamespace(advance_after_case_finish=AsyncMock()),
        result_sink=result_sink,
    )

    payload = {
        "schema": "dml-test-event@1",
        "event_id": "event-1",
        "task_id": "task-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "progress",
        "phase": "task_finish",
        "status": "PASSED",
        "total_cases": 1,
        "started_cases": 1,
        "finished_cases": 1,
        "failed_cases": 0,
    }

    with patch("app.modules.execution.application.event_ingest_service.ExecutionTaskDoc.find_one", _FindOneDoc(task_doc)):
        with patch("app.modules.execution.application.event_ingest_service.ExecutionTaskCaseDoc.find_one", _FindOneDoc(None)):
            await service.ingest_event("test-events", payload, {"offset": 1})

    result_sink.apply_execution_result.assert_awaited_once_with(
        task_id="task-1",
        overall_status="PASSED",
    )

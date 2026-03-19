from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService  # noqa: E402
from app.modules.execution.schemas.kafka_events import TestEvent as ExecutionTestEvent  # noqa: E402


class _FakeDispatchService:
    last_instance = None

    def __init__(self):
        self.build_calls = []
        self.dispatch_calls = []
        _FakeDispatchService.last_instance = self

    async def _build_task_dispatch_command(self, task_doc, dispatch_case_index):
        self.build_calls.append((task_doc.task_id, dispatch_case_index))
        return SimpleNamespace(
            dispatch_case_id=f"case-{dispatch_case_index + 1}",
            dispatch_case_index=dispatch_case_index,
        )

    async def _dispatch_existing_task(self, task_doc, command):
        self.dispatch_calls.append((task_doc.task_id, command.dispatch_case_index))
        task_doc.current_case_id = command.dispatch_case_id
        task_doc.current_case_index = command.dispatch_case_index


def test_test_event_accepts_single_layer_payload():
    """校验单层 progress 事件可以被新 schema 正常解析。"""
    event = ExecutionTestEvent.model_validate(
        {
            "schema": "bmc-test-event@1",
            "event_id": "eccaf0ae65f04bb390be3e062389ae90",
            "task_id": "custom_task_28df3852",
            "timestamp": "2026-03-18T01:10:09.837565+00:00",
            "event_type": "progress",
            "phase": "case_start",
            "total_cases": 2,
            "started_cases": 1,
            "finished_cases": 0,
            "failed_cases": 0,
            "case_id": "test_fan_basic_control",
            "case_title": "风扇基础功能测试",
            "project_tag": "universal",
            "nodeid": "tests/path.py::test_fan_basic_control",
        }
    )

    assert event.schema_name == "bmc-test-event@1"
    assert event.case_id == "test_fan_basic_control"
    assert event.started_cases == 1


def test_test_event_accepts_assert_payload():
    """校验 assert 事件支持 seq/name/data/error 等断言字段。"""
    event = ExecutionTestEvent.model_validate(
        {
            "schema": "bmc-test-event@1",
            "event_id": "b2c3d4e5f6789012345678901234abcd",
            "task_id": "test_single_case_12345",
            "timestamp": "2026-03-19T03:16:47.456Z",
            "project_tag": "universal",
            "case_id": "001_basic_check",
            "case_title": "电源基础功能测试",
            "event_type": "assert",
            "seq": 2,
            "name": "verify_bmc_connection",
            "status": "failed",
            "nodeid": "tests/universal/test_power_basic.py::test_power_on",
            "error": {
                "type": "AssertionError",
                "message": "BMC连接超时",
                "trace": "",
            },
            "data": {
                "timeout_seconds": 30,
                "actual_response_time": "timeout",
            },
        }
    )

    assert event.event_type == "assert"
    assert event.event_seq == 2
    assert event.assert_name == "verify_bmc_connection"
    assert event.error["message"] == "BMC连接超时"


@pytest.mark.asyncio
async def test_ingest_case_finish_event_updates_current_docs(monkeypatch):
    """校验 case_finish 会更新当前态任务与用例聚合结果，并推进下一条。"""
    service = ExecutionEventIngestService()
    event_doc_inserted: list[dict] = []

    task_doc = SimpleNamespace(
        task_id="custom_task_28df3852",
        case_count=2,
        reported_case_count=0,
        current_case_id="test_fan_basic_control",
        current_case_index=0,
        overall_status="QUEUED",
        consume_status="PENDING",
        started_case_count=0,
        finished_case_count=0,
        passed_case_count=0,
        failed_case_count=0,
        progress_percent=None,
        last_event_at=None,
        last_event_id=None,
        last_event_type=None,
        last_event_phase=None,
    )
    task_doc.save = _async_noop

    case_doc = SimpleNamespace(
        task_id="custom_task_28df3852",
        case_id="test_fan_basic_control",
        case_snapshot={"title": "风扇基础功能测试"},
        status="QUEUED",
        progress_percent=None,
        started_at=None,
        finished_at=None,
        last_seq=0,
        last_event_id=None,
        last_event_at=None,
        event_count=0,
        failure_message=None,
        nodeid=None,
        project_tag=None,
        case_title_snapshot=None,
        result_data={},
    )
    case_doc.save = _async_noop

    class FakeExecutionEventDoc:
        @staticmethod
        async def find_one(query):
            return None

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def insert(self):
            event_doc_inserted.append(self.kwargs)
            return self

    class FakeExecutionTaskDoc:
        @staticmethod
        async def find_one(query):
            return task_doc

    class FakeExecutionTaskCaseDoc:
        @staticmethod
        async def find_one(query):
            return case_doc

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)
    monkeypatch.setattr(ingest_module, "ExecutionService", _FakeDispatchService)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "test_single_case_c53631b9-test-event@1",
            "event_id": "eccaf0ae65f04bb390be3e062389ae90",
            "task_id": "custom_task_28df3852",
            "timestamp": "2026-03-18T01:10:09.837565+00:00",
            "event_type": "progress",
            "phase": "case_finish",
            "status": "FAILED",
            "total_cases": 2,
            "started_cases": 1,
            "finished_cases": 1,
            "failed_cases": 1,
            "case_id": "test_fan_basic_control",
            "case_title": "风扇基础功能测试",
            "project_tag": "universal",
            "nodeid": "tests/path.py::test_fan_basic_control",
        },
        metadata={"partition": 0, "offset": 1},
    )

    assert processed is True
    assert event_doc_inserted[0]["event_id"] == "eccaf0ae65f04bb390be3e062389ae90"
    assert case_doc.status == "FAILED"
    assert case_doc.event_count == 1
    assert case_doc.nodeid == "tests/path.py::test_fan_basic_control"
    assert case_doc.project_tag == "universal"
    assert task_doc.consume_status == "CONSUMED"
    assert task_doc.failed_case_count == 1
    assert task_doc.finished_case_count == 1
    assert task_doc.reported_case_count == 1
    assert task_doc.overall_status == "RUNNING"
    assert task_doc.current_case_id == "case-2"
    assert task_doc.current_case_index == 1


@pytest.mark.asyncio
async def test_ingest_case_finish_event_dispatches_next_case(monkeypatch):
    service = ExecutionEventIngestService()

    task_doc = SimpleNamespace(
        task_id="task-advance-1",
        case_count=2,
        reported_case_count=0,
        current_case_id="case-1",
        current_case_index=0,
        overall_status="RUNNING",
        consume_status="PENDING",
        dispatch_status="DISPATCHED",
        failed_case_count=0,
        finished_case_count=0,
        passed_case_count=0,
        started_case_count=0,
        progress_percent=None,
        stop_mode="NONE",
        last_event_at=None,
        last_event_id=None,
        last_event_type=None,
        last_event_phase=None,
        finished_at=None,
        last_callback_at=None,
    )
    task_doc.save = _async_noop

    case_doc = SimpleNamespace(
        task_id="task-advance-1",
        case_id="case-1",
        status="RUNNING",
        progress_percent=None,
        started_at=None,
        finished_at=None,
        last_seq=0,
        last_event_id=None,
        last_event_at=None,
        event_count=0,
        failure_message=None,
        nodeid=None,
        project_tag=None,
        case_title_snapshot=None,
        result_data={},
    )
    case_doc.save = _async_noop

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
            return case_doc

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)
    monkeypatch.setattr(ingest_module, "ExecutionService", _FakeDispatchService)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "demo-test-event@1",
            "event_id": "evt-case-finish-next",
            "task_id": "task-advance-1",
            "timestamp": "2026-03-18T01:10:09.837565+00:00",
            "event_type": "progress",
            "phase": "case_finish",
            "status": "PASSED",
            "total_cases": 2,
            "started_cases": 1,
            "finished_cases": 1,
            "failed_cases": 0,
            "case_id": "case-1",
        },
        metadata={"partition": 0, "offset": 9},
    )

    assert processed is True
    assert _FakeDispatchService.last_instance is not None
    assert _FakeDispatchService.last_instance.build_calls == [("task-advance-1", 1)]
    assert _FakeDispatchService.last_instance.dispatch_calls == [("task-advance-1", 1)]
    assert task_doc.current_case_id == "case-2"
    assert task_doc.current_case_index == 1
    assert task_doc.overall_status == "RUNNING"


@pytest.mark.asyncio
async def test_ingest_case_finish_event_marks_task_completed_on_last_case(monkeypatch):
    service = ExecutionEventIngestService()

    task_doc = SimpleNamespace(
        task_id="task-last-1",
        case_count=1,
        reported_case_count=0,
        current_case_id="case-1",
        current_case_index=0,
        overall_status="RUNNING",
        consume_status="PENDING",
        dispatch_status="DISPATCHED",
        failed_case_count=0,
        finished_case_count=0,
        passed_case_count=0,
        started_case_count=0,
        progress_percent=None,
        stop_mode="NONE",
        last_event_at=None,
        last_event_id=None,
        last_event_type=None,
        last_event_phase=None,
        finished_at=None,
        last_callback_at=None,
    )
    task_doc.save = _async_noop

    case_doc = SimpleNamespace(
        task_id="task-last-1",
        case_id="case-1",
        status="RUNNING",
        progress_percent=None,
        started_at=None,
        finished_at=None,
        last_seq=0,
        last_event_id=None,
        last_event_at=None,
        event_count=0,
        failure_message=None,
        nodeid=None,
        project_tag=None,
        case_title_snapshot=None,
        result_data={},
    )
    case_doc.save = _async_noop

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
            return case_doc

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)
    monkeypatch.setattr(ingest_module, "ExecutionService", _FakeDispatchService)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "demo-test-event@1",
            "event_id": "evt-case-finish-final",
            "task_id": "task-last-1",
            "timestamp": "2026-03-18T01:10:09.837565+00:00",
            "event_type": "progress",
            "phase": "case_finish",
            "status": "PASSED",
            "total_cases": 1,
            "started_cases": 1,
            "finished_cases": 1,
            "failed_cases": 0,
            "case_id": "case-1",
        },
        metadata={"partition": 0, "offset": 10},
    )

    assert processed is True
    assert task_doc.current_case_id is None
    assert task_doc.current_case_index == 1
    assert task_doc.overall_status == "PASSED"
    assert task_doc.dispatch_status == "COMPLETED"
    assert task_doc.finished_at is not None


@pytest.mark.asyncio
async def test_ingest_event_skips_duplicate_event(monkeypatch):
    """校验 event_id 幂等：重复事件不会重复处理。"""
    service = ExecutionEventIngestService()

    class FakeExecutionEventDoc:
        @staticmethod
        async def find_one(query):
            return SimpleNamespace(event_id=query["event_id"])

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "demo-test-event@1",
            "event_id": "duplicate-event-id",
            "task_id": "custom_task_28df3852",
            "timestamp": "2026-03-18T01:10:09.837565+00:00",
            "event_type": "progress",
            "phase": "case_finish",
            "total_cases": 1,
            "started_cases": 1,
            "finished_cases": 1,
            "failed_cases": 0,
            "case_id": "test_case",
            "case_title": "case",
            "project_tag": "universal",
            "nodeid": "tests/path.py::test_case",
        },
        metadata={"partition": 0, "offset": 1},
    )

    assert processed is False


@pytest.mark.asyncio
async def test_ingest_failed_assert_event_updates_step_counters(monkeypatch):
    """校验失败断言会累计步骤统计，并把断言明细写入 result_data。"""
    service = ExecutionEventIngestService()

    task_doc = SimpleNamespace(
        task_id="test_single_case_12345",
        case_count=5,
        reported_case_count=0,
        current_case_id="001_basic_check",
        current_case_index=0,
        overall_status="RUNNING",
        consume_status="PENDING",
        started_case_count=1,
        finished_case_count=0,
        passed_case_count=0,
        failed_case_count=0,
        progress_percent=0.0,
        last_event_at=None,
        last_event_id=None,
        last_event_type=None,
        last_event_phase=None,
        started_at=None,
        finished_at=None,
        last_callback_at=None,
    )
    task_doc.save = _async_noop

    case_doc = SimpleNamespace(
        task_id="test_single_case_12345",
        case_id="001_basic_check",
        case_snapshot={"title": "电源基础功能测试"},
        status="RUNNING",
        progress_percent=None,
        started_at=None,
        finished_at=None,
        last_seq=0,
        last_event_id=None,
        last_event_at=None,
        event_count=0,
        failure_message=None,
        nodeid=None,
        project_tag=None,
        case_title_snapshot=None,
        result_data={},
        step_total=0,
        step_passed=0,
        step_failed=0,
        step_skipped=0,
    )
    case_doc.save = _async_noop

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
            return case_doc

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "bmc-test-event@1",
            "event_id": "b2c3d4e5f6789012345678901234abcd",
            "task_id": "test_single_case_12345",
            "timestamp": "2026-03-19T03:16:47.456Z",
            "project_tag": "universal",
            "case_id": "001_basic_check",
            "case_title": "电源基础功能测试",
            "event_type": "assert",
            "seq": 2,
            "name": "verify_bmc_connection",
            "status": "failed",
            "nodeid": "tests/universal/test_power_basic.py::test_power_on",
            "error": {
                "type": "AssertionError",
                "message": "BMC连接超时",
                "trace": "",
            },
            "data": {
                "timeout_seconds": 30,
                "actual_response_time": "timeout",
            },
        },
        metadata={"partition": 0, "offset": 2},
    )

    assert processed is True
    assert case_doc.step_total == 1
    assert case_doc.step_failed == 1
    assert case_doc.failure_message == "BMC连接超时"
    assert case_doc.result_data["assertions"][0]["name"] == "verify_bmc_connection"
    assert task_doc.consume_status == "CONSUMED"


async def _async_noop():
    """测试替身使用的异步空 save。"""
    return None

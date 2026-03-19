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
async def test_ingest_case_finish_event_updates_current_and_history_docs(monkeypatch):
    """校验 case_finish 会同时更新当前态与历史态的聚合结果。"""
    service = ExecutionEventIngestService()
    event_doc_inserted: list[dict] = []

    # 当前任务主记录：用于断言任务级聚合统计是否被正确回填。
    task_doc = SimpleNamespace(
        task_id="custom_task_28df3852",
        current_run_no=3,
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

    # 当前 run 记录：用于断言 run 级统计是否同步更新。
    run_doc = SimpleNamespace(
        task_id="custom_task_28df3852",
        run_no=3,
        overall_status="QUEUED",
        reported_case_count=0,
        started_case_count=0,
        finished_case_count=0,
        passed_case_count=0,
        failed_case_count=0,
        progress_percent=None,
        event_count=0,
        last_event_at=None,
    )
    run_doc.save = _async_noop

    # 当前 case 工作表：用于断言当前态 case 是否正确标记为 FAILED。
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

    # 历史 run_case：用于断言历史态 case 是否同步保存结果。
    run_case_doc = SimpleNamespace(
        task_id="custom_task_28df3852",
        run_no=3,
        case_id="test_fan_basic_control",
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
        phase=None,
        result_data={},
    )
    run_case_doc.save = _async_noop

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

    class FakeExecutionTaskRunDoc:
        @staticmethod
        async def find_one(query):
            return run_doc

    class FakeExecutionTaskRunCaseDoc:
        @staticmethod
        async def find_one(query):
            return run_case_doc

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskRunDoc", FakeExecutionTaskRunDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskRunCaseDoc", FakeExecutionTaskRunCaseDoc)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "test_single_case_c53631b9-test-event@1",
            "event_id": "eccaf0ae65f04bb390be3e062389ae90",
            "task_id": "custom_task_28df3852",
            "run_no": 3,
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
    assert run_case_doc.status == "FAILED"
    assert run_case_doc.phase == "case_finish"
    assert task_doc.consume_status == "CONSUMED"
    assert task_doc.failed_case_count == 1
    assert task_doc.finished_case_count == 1
    assert task_doc.reported_case_count == 1
    assert task_doc.overall_status == "RUNNING"
    assert run_doc.failed_case_count == 1
    assert run_doc.finished_case_count == 1
    assert run_doc.reported_case_count == 1


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

    # 任务和 run 在 assert 事件里主要验证不会被错误覆盖。
    task_doc = SimpleNamespace(
        task_id="test_single_case_12345",
        current_run_no=1,
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

    run_doc = SimpleNamespace(
        task_id="test_single_case_12345",
        run_no=1,
        overall_status="RUNNING",
        reported_case_count=0,
        started_case_count=1,
        finished_case_count=0,
        passed_case_count=0,
        failed_case_count=0,
        progress_percent=0.0,
        event_count=0,
        last_event_at=None,
        started_at=None,
        finished_at=None,
        last_callback_at=None,
    )
    run_doc.save = _async_noop

    # case 当前态：重点验证 step_total/step_failed/failure_message/assertions。
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

    # case 历史态：重点验证历史记录也能保留断言细节。
    run_case_doc = SimpleNamespace(
        task_id="test_single_case_12345",
        run_no=1,
        case_id="001_basic_check",
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
        phase=None,
        result_data={},
        step_total=0,
        step_passed=0,
        step_failed=0,
        step_skipped=0,
    )
    run_case_doc.save = _async_noop

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

    class FakeExecutionTaskRunDoc:
        @staticmethod
        async def find_one(query):
            return run_doc

    class FakeExecutionTaskRunCaseDoc:
        @staticmethod
        async def find_one(query):
            return run_case_doc

    import app.modules.execution.application.event_ingest_service as ingest_module

    monkeypatch.setattr(ingest_module, "ExecutionEventDoc", FakeExecutionEventDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskDoc", FakeExecutionTaskDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskRunDoc", FakeExecutionTaskRunDoc)
    monkeypatch.setattr(ingest_module, "ExecutionTaskRunCaseDoc", FakeExecutionTaskRunCaseDoc)

    processed = await service.ingest_event(
        topic="test-events",
        event_payload={
            "schema": "bmc-test-event@1",
            "event_id": "b2c3d4e5f6789012345678901234abcd",
            "task_id": "test_single_case_12345",
            "run_no": 1,
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
    assert run_case_doc.step_total == 1
    assert run_case_doc.step_failed == 1
    assert run_case_doc.result_data["assertions"][0]["status"] == "failed"


async def _async_noop():
    """测试替身使用的异步空 save。"""
    return None

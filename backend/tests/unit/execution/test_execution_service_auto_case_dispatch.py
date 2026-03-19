from types import SimpleNamespace
from datetime import timezone

import pytest

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.execution_service import ExecutionService
from app.modules.execution.application import execution_service as service_module
from app.modules.execution.application.progress_mixin import ExecutionProgressMixin
from app.modules.execution.application.query_mixin import ExecutionTaskQueryMixin
from app.modules.execution.schemas.execution import DispatchCaseItem, DispatchTaskRequest
from app.modules.execution.service.task_dispatcher import DispatchResult
from app.modules.test_specs.repository.models.test_case import TestCaseStep


@pytest.mark.asyncio
async def test_resolve_case_ids_by_auto_case_ids(monkeypatch):
    auto_docs = [
        SimpleNamespace(
            auto_case_id="ATC-2026-00002",
            source_case_id="001_basic_check",
        ),
        SimpleNamespace(
            auto_case_id="ATC-2026-00003",
            source_case_id="002_power_cycle",
        ),
    ]
    test_case_docs = [
        SimpleNamespace(case_id="001_basic_check"),
        SimpleNamespace(case_id="002_power_cycle"),
    ]

    class FakeAutoQuery:
        async def to_list(self):
            return auto_docs

    class FakeTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            class _Query:
                async def to_list(self_inner):
                    return test_case_docs
            return _Query()

    class FakeAutomationTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            return FakeAutoQuery()

    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)
    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)

    result = await ExecutionService.resolve_case_ids_by_auto_case_ids(
        ["ATC-2026-00003", "ATC-2026-00002"]
    )

    assert result == ["002_power_cycle", "001_basic_check"]


@pytest.mark.asyncio
async def test_resolve_case_ids_by_auto_case_ids_rejects_ambiguous_mapping(monkeypatch):
    auto_docs = [
        SimpleNamespace(
            auto_case_id="ATC-2026-00002",
            source_case_id="001_basic_check",
        ),
    ]
    test_case_docs = [
        SimpleNamespace(case_id="001_basic_check"),
        SimpleNamespace(case_id="001_basic_check"),
    ]

    class FakeAutoQuery:
        async def to_list(self):
            return auto_docs

    class FakeTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            class _Query:
                async def to_list(self_inner):
                    return test_case_docs
            return _Query()

    class FakeAutomationTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            return FakeAutoQuery()

    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)
    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)

    with pytest.raises(ValueError, match="multiple test cases"):
        await ExecutionService.resolve_case_ids_by_auto_case_ids(["ATC-2026-00002"])


@pytest.mark.asyncio
async def test_resolve_case_ids_by_auto_case_ids_rejects_missing_auto_case(monkeypatch):
    class FakeAutoQuery:
        async def to_list(self):
            return []

    class FakeAutomationTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            return FakeAutoQuery()

    class FakeTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            class _Query:
                async def to_list(self_inner):
                    return []
            return _Query()

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)

    with pytest.raises(KeyError, match="Automation test cases not found"):
        await ExecutionService.resolve_case_ids_by_auto_case_ids(["ATC-2026-99999"])


@pytest.mark.asyncio
async def test_resolve_case_ids_by_auto_case_ids_rejects_unmatched_source_case_id(monkeypatch):
    auto_docs = [
        SimpleNamespace(
            auto_case_id="ATC-2026-00002",
            source_case_id="TC-2026-00003",
        ),
    ]

    class FakeAutoQuery:
        async def to_list(self):
            return auto_docs

    class FakeAutomationTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            return FakeAutoQuery()

    class FakeTestCaseDoc:
        @staticmethod
        def find(*args, **kwargs):
            class _Query:
                async def to_list(self_inner):
                    return []
            return _Query()

    monkeypatch.setattr(service_module, "AutomationTestCaseDoc", FakeAutomationTestCaseDoc)
    monkeypatch.setattr(service_module, "TestCaseDoc", FakeTestCaseDoc)

    with pytest.raises(KeyError, match="source_case_id not matched to test cases"):
        await ExecutionService.resolve_case_ids_by_auto_case_ids(["ATC-2026-00002"])


def test_dispatch_command_includes_auto_case_id_in_payload():
    command = DispatchExecutionTaskCommand(
        task_id="ET-2026-000001",
        external_task_id="EXT-ET-2026-000001",
        framework="pytest",
        trigger_source="manual",
        created_by="user-1",
        auto_case_ids=["ATC-2026-00002"],
        case_ids=["TC-001"],
        dispatch_case_id="TC-001",
        dispatch_auto_case_id="ATC-2026-00002",
    )

    assert command.kafka_task_data["current_case_id"] == "TC-001"
    assert command.kafka_task_data["current_auto_case_id"] == "ATC-2026-00002"
    assert command.kafka_task_data["cases"] == [
        {"case_id": "TC-001", "auto_case_id": "ATC-2026-00002"}
    ]


def test_dispatch_request_accepts_legacy_case_id_field_as_auto_case_id():
    request = DispatchTaskRequest(
        framework="CaseMetadata",
        agent_id="fake-framework-agent",
        trigger_source="web_ui",
        cases=[DispatchCaseItem(case_id="ATC-2026-00002")],
    )

    assert request.cases[0].auto_case_id == "ATC-2026-00002"


def test_dispatch_request_rejects_conflicting_case_identifiers():
    with pytest.raises(ValueError, match="must match"):
        DispatchCaseItem(case_id="ATC-2026-00002", auto_case_id="ATC-2026-99999")


def test_serialize_task_doc_includes_auto_case_identifiers():
    task_doc = SimpleNamespace(
        task_id="ET-2026-000001",
        external_task_id="EXT-ET-2026-000001",
        framework="CaseMetadata",
        agent_id="fake-framework-agent",
        dispatch_channel="KAFKA",
        dedup_key="dedup-key",
        schedule_type="IMMEDIATE",
        schedule_status="TRIGGERED",
        dispatch_status="DISPATCHED",
        consume_status="PENDING",
        overall_status="QUEUED",
        case_count=1,
        latest_run_no=1,
        current_run_no=1,
        current_case_id="TC-2026-00003",
        current_case_index=0,
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
                {"case_id": "TC-2026-00003", "auto_case_id": "ATC-2026-00013"}
            ],
        },
    )

    result = ExecutionTaskQueryMixin._serialize_task_doc(task_doc)

    assert result["current_auto_case_id"] == "ATC-2026-00013"
    assert result["auto_case_ids"] == ["ATC-2026-00013"]


def test_build_case_snapshot_contains_static_execution_context():
    case_doc = SimpleNamespace(
        case_id="TC-2026-00003",
        ref_req_id="REQ-2026-00001",
        workflow_item_id="WI-1",
        title="风扇基础功能测试",
        version=3,
        status="approved",
        priority="P1",
        tags=["fan", "smoke"],
        test_category="functional",
        estimated_duration_sec=300,
        target_components=["fan"],
        required_env={"os": "linux"},
        tooling_req=["ipmitool"],
        is_destructive=False,
        pre_condition="device online",
        post_condition="device healthy",
        steps=[TestCaseStep(step_id="S1", name="step1", action="do", expected="ok")],
        cleanup_steps=[TestCaseStep(step_id="C1", name="cleanup", action="undo", expected="ok")],
        custom_fields={"suite": "fan"},
    )

    snapshot = ExecutionService._build_case_snapshot(case_doc, auto_case_id="ATC-2026-00013")

    assert snapshot["case_id"] == "TC-2026-00003"
    assert snapshot["auto_case_id"] == "ATC-2026-00013"
    assert snapshot["ref_req_id"] == "REQ-2026-00001"
    assert snapshot["title"] == "风扇基础功能测试"
    assert snapshot["required_env"] == {"os": "linux"}
    assert snapshot["steps"][0]["step_id"] == "S1"
    assert snapshot["cleanup_steps"][0]["step_id"] == "C1"


def test_build_case_dispatch_command_accepts_iso_planned_at():
    task_doc = SimpleNamespace(
        task_id="ET-2026-000001",
        external_task_id="EXT-ET-2026-000001",
        framework="CaseMetadata",
        agent_id="fake-framework-agent",
        created_by="u-admin",
        current_run_no=1,
        schedule_type="SCHEDULED",
        request_payload={
            "trigger_source": "manual",
            "planned_at": "2026-03-18T16:49:00+00:00",
            "callback_url": "http://localhost:8000/callback",
            "dut": {"device_id": "DUT-001"},
        },
    )

    command = ExecutionService._build_case_dispatch_command(
        task_doc=task_doc,
        case_ids=["TC-2026-00003"],
        auto_case_ids=["ATC-2026-00013"],
        dispatch_case_index=0,
    )

    assert command.planned_at is not None
    assert command.planned_at.isoformat() == "2026-03-18T16:49:00+00:00"
    assert command.planned_at.tzinfo == timezone.utc


def test_apply_case_status_payload_keeps_case_snapshot_static():
    mixin = ExecutionProgressMixin()
    case_doc = SimpleNamespace(
        status="QUEUED",
        progress_percent=None,
        step_total=0,
        step_passed=0,
        step_failed=0,
        step_skipped=0,
        started_at=None,
        finished_at=None,
        last_event_id=None,
        last_seq=0,
        case_snapshot={"case_id": "TC-2026-00003", "auto_case_id": "ATC-2026-00013"},
        result_data={},
    )

    mixin._apply_case_status_payload(
        case_doc,
        {
            "status": "RUNNING",
            "seq": 1,
            "result_data": {"stdout": "hello"},
        },
        "RUNNING",
    )

    assert case_doc.case_snapshot == {"case_id": "TC-2026-00003", "auto_case_id": "ATC-2026-00013"}
    assert case_doc.result_data == {"stdout": "hello"}


@pytest.mark.asyncio
async def test_dispatch_existing_task_keeps_schedule_status_for_dispatch_failure(monkeypatch):
    service = ExecutionService()

    class FakeDispatcher:
        async def dispatch(self, command):
            return DispatchResult(
                success=False,
                channel="KAFKA",
                message="dispatch failed",
                response={"accepted": False, "message": "dispatch failed"},
                error="dispatch failed",
            )

    class FakeCaseDoc:
        def __init__(self):
            self.dispatch_attempts = 0
            self.dispatch_status = "PENDING"
            self.dispatched_at = None
            self.case_id = "TC-2026-00003"

        async def save(self):
            return None

    task_doc = SimpleNamespace(
        task_id="ET-2026-000001",
        current_run_no=0,
        dispatch_channel="KAFKA",
        dispatch_status="DISPATCHING",
        dispatch_error=None,
        dispatch_response={},
        schedule_status="READY",
        overall_status="QUEUED",
        current_case_id="TC-2026-00003",
        current_case_index=0,
        triggered_at=None,
        finished_at=None,
        save=lambda: None,
    )

    async def fake_task_save():
        return None

    task_doc.save = fake_task_save
    case_doc = FakeCaseDoc()

    class FakeExecutionTaskCaseDoc:
        @staticmethod
        async def find_one(*args, **kwargs):
            return case_doc

    monkeypatch.setattr(service, "_dispatcher", FakeDispatcher())
    monkeypatch.setattr(service_module, "ExecutionTaskCaseDoc", FakeExecutionTaskCaseDoc)

    command = DispatchExecutionTaskCommand(
        task_id="ET-2026-000001",
        external_task_id="EXT-ET-2026-000001",
        framework="CaseMetadata",
        trigger_source="web_ui",
        created_by="user-1",
        auto_case_ids=["ATC-2026-00013"],
        case_ids=["TC-2026-00003"],
        dispatch_case_id="TC-2026-00003",
        dispatch_auto_case_id="ATC-2026-00013",
        dispatch_case_index=0,
    )

    await service._dispatch_existing_task(task_doc, command)

    assert task_doc.schedule_status == "TRIGGERED"
    assert task_doc.dispatch_status == "DISPATCH_FAILED"
    assert task_doc.overall_status == "FAILED"
    assert task_doc.triggered_at is not None
    assert task_doc.finished_at is not None
    assert case_doc.dispatch_attempts == 1
    assert case_doc.dispatch_status == "DISPATCH_FAILED"

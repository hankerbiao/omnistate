from datetime import datetime, timezone

import pytest

from app.modules.execution.application.execution_service import ExecutionService


class _FakeCountQuery:
    def __init__(self, count_value):
        self._count_value = count_value

    async def count(self):
        return self._count_value


class _FakeTaskDoc:
    def __init__(self):
        self.task_id = "ET-2026-000001"
        self.overall_status = "QUEUED"
        self.dispatch_status = "DISPATCHED"
        self.consume_status = "PENDING"
        self.reported_case_count = 0
        self.started_at = None
        self.finished_at = None
        self.last_callback_at = None
        self.dispatch_response = {}
        self.dispatch_error = None
        self.updated_at = datetime.now(timezone.utc)
        self.is_deleted = False
        self.saved = False

    async def save(self):
        self.saved = True
        self.updated_at = datetime.now(timezone.utc)


class _FakeCaseDoc:
    def __init__(self):
        self.task_id = "ET-2026-000001"
        self.case_id = "TC-001"
        self.status = "QUEUED"
        self.progress_percent = None
        self.step_total = 0
        self.step_passed = 0
        self.step_failed = 0
        self.step_skipped = 0
        self.last_seq = 0
        self.last_event_id = None
        self.started_at = None
        self.finished_at = None
        self.case_snapshot = {}
        self.updated_at = datetime.now(timezone.utc)
        self.saved = False

    async def save(self):
        self.saved = True
        self.updated_at = datetime.now(timezone.utc)


class _FakeEventDoc:
    def __init__(self, **kwargs):
        self.task_id = kwargs["task_id"]
        self.event_id = kwargs["event_id"]
        self.event_type = kwargs["event_type"]
        self.seq = kwargs["seq"]
        self.received_at = datetime.now(timezone.utc)
        self.processed = kwargs.get("processed", False)
        self.inserted = False

    async def insert(self):
        self.inserted = True


class _FakeEventDocFactory:
    inserted_events = []
    existing_event = None

    def __init__(self, **kwargs):
        self._event = _FakeEventDoc(**kwargs)
        self.__dict__.update(self._event.__dict__)
        _FakeEventDocFactory.inserted_events.append(self)

    async def insert(self):
        await self._event.insert()
        self.inserted = self._event.inserted

    @classmethod
    async def find_one(cls, *args, **kwargs):
        return cls.existing_event


@pytest.mark.asyncio
async def test_report_task_event_inserts_new_event(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc()
    _FakeEventDocFactory.inserted_events = []
    _FakeEventDocFactory.existing_event = None

    async def fake_task_find_one(query, *args, **kwargs):
        if query.get("task_id") == task_doc.task_id:
            return task_doc
        return None

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_task_find_one,
    )
    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionEventDoc",
        _FakeEventDocFactory,
    )

    result = await service.report_task_event(
        task_doc.task_id,
        {
            "event_id": "evt-1",
            "event_type": "task_started",
            "seq": 1,
            "payload": {"foo": "bar"},
        },
    )

    assert result["event_id"] == "evt-1"
    assert result["event_type"] == "TASK_STARTED"
    assert task_doc.overall_status == "RUNNING"
    assert task_doc.saved is True
    assert _FakeEventDocFactory.inserted_events[0].inserted is True


@pytest.mark.asyncio
async def test_report_case_status_rejects_stale_seq(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc()
    case_doc = _FakeCaseDoc()
    case_doc.last_seq = 10
    case_doc.status = "RUNNING"

    async def fake_task_find_one(query, *args, **kwargs):
        if query.get("task_id") == task_doc.task_id:
            return task_doc
        return None

    async def fake_case_find_one(query, *args, **kwargs):
        if query.get("task_id") == case_doc.task_id and query.get("case_id") == case_doc.case_id:
            return case_doc
        return None

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_task_find_one,
    )
    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskCaseDoc.find_one",
        fake_case_find_one,
    )

    result = await service.report_case_status(
        task_doc.task_id,
        case_doc.case_id,
        {"status": "FAILED", "seq": 9},
    )

    assert result["accepted"] is False
    assert result["status"] == "RUNNING"
    assert case_doc.saved is False


@pytest.mark.asyncio
async def test_complete_task_updates_final_status(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc()
    _FakeEventDocFactory.inserted_events = []
    _FakeEventDocFactory.existing_event = None

    async def fake_task_find_one(query, *args, **kwargs):
        if query.get("task_id") == task_doc.task_id:
            return task_doc
        return None

    def fake_case_find(*args, **kwargs):
        return _FakeCountQuery(2)

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_task_find_one,
    )
    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionEventDoc",
        _FakeEventDocFactory,
    )
    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskCaseDoc.find",
        fake_case_find,
    )

    result = await service.complete_task(
        task_doc.task_id,
        {
            "status": "PASSED",
            "event_id": "evt-complete",
            "seq": 99,
            "summary": {"passed": 2},
            "executor": "agent-01",
        },
    )

    assert result["overall_status"] == "PASSED"
    assert result["dispatch_status"] == "COMPLETED"
    assert result["reported_case_count"] == 2
    assert task_doc.dispatch_response["passed"] == 2
    assert task_doc.dispatch_response["executor"] == "agent-01"
    assert _FakeEventDocFactory.inserted_events[0].inserted is True

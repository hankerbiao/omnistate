from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.modules.execution.application.execution_service import ExecutionService


class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self):
        return self._docs


class _FakeTaskDoc:
    def __init__(self, schedule_status="PENDING"):
        self.task_id = "ET-2026-000001"
        self.external_task_id = "EXT-ET-2026-000001"
        self.framework = "pytest"
        self.agent_id = "agent-01"
        self.dispatch_channel = "HTTP"
        self.dedup_key = "old-key"
        self.schedule_type = "SCHEDULED"
        self.schedule_status = schedule_status
        self.dispatch_status = "PENDING"
        self.consume_status = "PENDING"
        self.overall_status = "QUEUED"
        self.request_payload = {
            "trigger_source": "manual",
            "callback_url": "http://callback",
            "dut": {"region": "cn"},
            "runtime_config": {"env": "sit"},
            "cases": [{"case_id": "TC-001"}],
        }
        self.dispatch_response = {}
        self.dispatch_error = None
        self.created_by = "user-1"
        self.case_count = 1
        self.planned_at = datetime.now(timezone.utc) + timedelta(hours=1)
        self.triggered_at = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.is_deleted = False
        self.saved = False

    async def save(self):
        self.saved = True
        self.updated_at = datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_cancel_scheduled_task_updates_status(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc()

    async def fake_find_one(*args, **kwargs):
        return task_doc

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_find_one,
    )

    result = await service.cancel_scheduled_task(task_doc.task_id, actor_id="user-1")

    assert result["schedule_status"] == "CANCELLED"
    assert result["dispatch_status"] == "CANCELLED"
    assert result["overall_status"] == "CANCELLED"
    assert task_doc.saved is True


@pytest.mark.asyncio
async def test_cancel_scheduled_task_rejects_non_pending(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc(schedule_status="TRIGGERED")

    async def fake_find_one(*args, **kwargs):
        return task_doc

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_find_one,
    )

    with pytest.raises(ValueError, match="cannot be changed"):
        await service.cancel_scheduled_task(task_doc.task_id, actor_id="user-1")


@pytest.mark.asyncio
async def test_update_scheduled_task_refreshes_payload(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc()
    new_planned_at = datetime.now(timezone.utc) + timedelta(hours=2)
    case_docs = [
        SimpleNamespace(case_id="TC-001", title="A", version=1, priority="P1", status="READY"),
        SimpleNamespace(case_id="TC-002", title="B", version=1, priority="P2", status="READY"),
    ]

    async def fake_find_one(query, *args, **kwargs):
        if query.get("task_id") == task_doc.task_id and "$ne" not in query.get("task_id", {}):
            return task_doc
        if query.get("dedup_key"):
            return None
        return None

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_find_one,
    )
    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.TestCaseDoc.find",
        lambda *args, **kwargs: _FakeQuery(case_docs),
    )

    async def fake_replace_task_case_docs(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_replace_task_case_docs", fake_replace_task_case_docs)

    result = await service.update_scheduled_task(
        task_doc.task_id,
        actor_id="user-1",
        payload={
            "agent_id": "agent-02",
            "planned_at": new_planned_at,
            "cases": [{"case_id": "TC-001"}, {"case_id": "TC-002"}],
            "runtime_config": {"env": "uat"},
        },
    )

    assert result["schedule_status"] == "PENDING"
    assert result["agent_id"] == "agent-02"
    assert result["case_count"] == 2
    assert task_doc.request_payload["runtime_config"] == {"env": "uat"}
    assert task_doc.request_payload["cases"] == [{"case_id": "TC-001"}, {"case_id": "TC-002"}]
    assert task_doc.saved is True

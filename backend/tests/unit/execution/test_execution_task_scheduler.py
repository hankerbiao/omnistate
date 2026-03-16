from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.execution.service.task_scheduler import ExecutionTaskScheduler


class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self):
        return self._docs


@pytest.mark.asyncio
async def test_scheduler_dispatches_due_tasks(monkeypatch):
    scheduler = ExecutionTaskScheduler()
    saved_states = []
    dispatched = []

    class _FakeTaskDoc:
        def __init__(self):
            self.task_id = "ET-2026-000001"
            self.external_task_id = "EXT-ET-2026-000001"
            self.framework = "pytest"
            self.agent_id = "agent-01"
            self.request_payload = {
                "trigger_source": "manual",
                "cases": [{"case_id": "TC-001"}],
                "callback_url": None,
                "dut": {},
                "runtime_config": {},
            }
            self.created_by = "user-1"
            self.schedule_type = "SCHEDULED"
            self.schedule_status = "PENDING"
            self.planned_at = datetime(2026, 3, 15, tzinfo=timezone.utc)

        async def save(self):
            saved_states.append(self.schedule_status)

    fake_doc = _FakeTaskDoc()

    monkeypatch.setattr(
        "app.modules.execution.service.task_scheduler.ExecutionTaskDoc.find",
        lambda *args, **kwargs: _FakeQuery([fake_doc]),
    )

    async def fake_dispatch_existing_task(task_doc, command):
        dispatched.append((task_doc.task_id, command.schedule_type))

    monkeypatch.setattr(scheduler._service, "_dispatch_existing_task", fake_dispatch_existing_task)

    count = await scheduler.dispatch_due_tasks()

    assert count == 1
    assert saved_states == ["READY"]
    assert dispatched == [("ET-2026-000001", "SCHEDULED")]

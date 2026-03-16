from types import SimpleNamespace

import pytest

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.execution_service import ExecutionService


class _FakeQuery:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self):
        return self._docs


class _FakeTaskDoc:
    def __init__(self, task_id="ET-2026-000001"):
        self.task_id = task_id
        self.consume_status = "PENDING"
        self.consumed_at = None
        self.is_deleted = False
        self.dispatch_response = {}
        self.saved = False

    async def save(self):
        self.saved = True


def _build_command() -> DispatchExecutionTaskCommand:
    return DispatchExecutionTaskCommand(
        task_id="ET-2026-000001",
        external_task_id="EXT-ET-2026-000001",
        framework="pytest",
        trigger_source="manual",
        created_by="user-1",
        case_ids=["TC-002", "TC-001"],
        callback_url="http://callback",
        dut={"region": "cn"},
        runtime_config={"env": "sit"},
    )


def test_build_dedup_key_is_stable_for_case_order():
    command_a = _build_command()
    command_b = DispatchExecutionTaskCommand(
        task_id="ET-2026-000002",
        external_task_id="EXT-ET-2026-000002",
        framework="pytest",
        trigger_source="manual",
        created_by="user-9",
        case_ids=["TC-001", "TC-002"],
        callback_url="http://callback",
        dut={"region": "cn"},
        runtime_config={"env": "sit"},
    )

    assert ExecutionService._build_dedup_key(command_a) == ExecutionService._build_dedup_key(command_b)


@pytest.mark.asyncio
async def test_dispatch_blocks_when_pending_duplicate_exists(monkeypatch):
    service = ExecutionService()
    command = _build_command()
    case_docs = [
        SimpleNamespace(case_id="TC-001", title="A", version=1, priority="P1", status="READY"),
        SimpleNamespace(case_id="TC-002", title="B", version=1, priority="P1", status="READY"),
    ]
    pending_task = SimpleNamespace(task_id="ET-2026-000099")

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.TestCaseDoc.find",
        lambda *args, **kwargs: _FakeQuery(case_docs),
    )
    async def fake_find_one(*args, **kwargs):
        return pending_task
    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_find_one,
    )

    with pytest.raises(ValueError, match="not yet consumed"):
        await service.dispatch_execution_task(command, actor_id="user-1")


@pytest.mark.asyncio
async def test_ack_task_consumed_updates_status(monkeypatch):
    service = ExecutionService()
    task_doc = _FakeTaskDoc()

    async def fake_find_one(*args, **kwargs):
        return task_doc

    monkeypatch.setattr(
        "app.modules.execution.application.execution_service.ExecutionTaskDoc.find_one",
        fake_find_one,
    )

    result = await service.ack_task_consumed("ET-2026-000001", consumer_id="consumer-1")

    assert result["task_id"] == "ET-2026-000001"
    assert result["consume_status"] == "CONSUMED"
    assert task_doc.dispatch_response["consumer_id"] == "consumer-1"
    assert task_doc.saved is True

from types import SimpleNamespace

import pytest

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher


def _build_command(agent_id=None):
    return DispatchExecutionTaskCommand(
        task_id="ET-2026-000001",
        external_task_id="EXT-ET-2026-000001",
        framework="pytest",
        trigger_source="manual",
        created_by="user-1",
        case_ids=["TC-001"],
        agent_id=agent_id,
    )


@pytest.mark.asyncio
async def test_dispatch_uses_kafka_by_default(monkeypatch):
    dispatcher = ExecutionTaskDispatcher()

    monkeypatch.setattr(
        "app.modules.execution.service.task_dispatcher.settings.EXECUTION_DISPATCH_MODE",
        "kafka",
    )
    expected = SimpleNamespace(success=True, channel="KAFKA", message="ok", response={})
    monkeypatch.setattr(dispatcher, "_dispatch_via_kafka", lambda command: expected)

    result = await dispatcher.dispatch(_build_command())

    assert result is expected


@pytest.mark.asyncio
async def test_http_dispatch_requires_agent_id(monkeypatch):
    dispatcher = ExecutionTaskDispatcher()
    monkeypatch.setattr(
        "app.modules.execution.service.task_dispatcher.settings.EXECUTION_DISPATCH_MODE",
        "http",
    )

    result = await dispatcher.dispatch(_build_command())

    assert result.success is False
    assert result.channel == "HTTP"
    assert "agent_id is required" in result.message


@pytest.mark.asyncio
async def test_http_dispatch_rejects_offline_agent(monkeypatch):
    dispatcher = ExecutionTaskDispatcher()
    monkeypatch.setattr(
        "app.modules.execution.service.task_dispatcher.settings.EXECUTION_DISPATCH_MODE",
        "http",
    )

    async def fake_find_one(*args, **kwargs):
        return SimpleNamespace(status="OFFLINE", base_url="http://agent", agent_id="agent-1")

    monkeypatch.setattr(
        "app.modules.execution.service.task_dispatcher.ExecutionAgentDoc.find_one",
        fake_find_one,
    )

    result = await dispatcher.dispatch(_build_command(agent_id="agent-1"))

    assert result.success is False
    assert "not online" in result.message

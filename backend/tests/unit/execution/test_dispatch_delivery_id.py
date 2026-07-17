"""RabbitMQ 执行消息稳定投递标识测试。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher


@pytest.mark.asyncio
async def test_dispatch_uses_stable_task_and_case_delivery_id(monkeypatch):
    manager = SimpleNamespace(send_task_async=AsyncMock(return_value=True))
    monkeypatch.setattr(
        "app.shared.infrastructure.get_rabbitmq_manager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "app.modules.execution.application.task_command_helpers.build_dispatch_task_data",
        lambda _command: {"action": "create", "data": {}},
    )
    command = SimpleNamespace(task_id="task-1", dispatch_case_id="case-2")

    result = await ExecutionTaskDispatcher().dispatch(command)

    assert result.success is True
    message = manager.send_task_async.await_args.args[0]
    assert message.delivery_id == "task-1:case-2"
    assert message.task_data["delivery_id"] == "task-1:case-2"

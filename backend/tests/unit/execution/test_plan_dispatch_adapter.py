"""执行计划派发适配器单元测试。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.execution.application.plan_dispatch_adapter import PlanDispatchAdapter


async def test_dispatch_task_builds_request_with_correct_fields() -> None:
    """dispatch_task 正确传递所有参数到 ExecutionTaskCommandService。"""
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-1"})
    adapter = PlanDispatchAdapter(task_command_service=mock_service)

    mock_seq = MagicMock()
    mock_seq.next = AsyncMock(return_value=42)

    with patch("app.modules.execution.application.plan_dispatch_adapter.SequenceIdService") as mock_seq_cls:
        mock_seq_cls.return_value = mock_seq
        await adapter.dispatch_task(
            item_id="EPI-1",
            case_id="AUTO-1",
            plan_id="EP-1",
            actor_id="u-1",
            agent_id="agent-A",
            schedule_type="IMMEDIATE",
            pytest_options={"verbose": True},
            timeout=300,
        )

    mock_service.create_and_dispatch_task.assert_awaited_once()
    call_kwargs = mock_service.create_and_dispatch_task.call_args.kwargs
    request = call_kwargs["request"]
    assert request.trigger_source == "execution_plan:EP-1:EPI-1"
    assert request.agent_id == "agent-A"
    assert request.schedule_type == "IMMEDIATE"
    assert request.timeout == 300
    assert call_kwargs["actor_id"] == "u-1"
    assert call_kwargs["skip_dedup"] is True
    assert len(request.cases) == 1
    assert request.cases[0].auto_case_id == "AUTO-1"


async def test_dispatch_task_uses_plan_item_as_category() -> None:
    """category 未指定时使用 {plan_id}/{item_id}。"""
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-1"})
    adapter = PlanDispatchAdapter(task_command_service=mock_service)

    with patch("app.modules.execution.application.plan_dispatch_adapter.SequenceIdService"):
        await adapter.dispatch_task(
            item_id="EPI-2",
            case_id="AUTO-2",
            plan_id="EP-2",
            actor_id="u-1",
            agent_id="agent-A",
        )

    request = mock_service.create_and_dispatch_task.call_args.kwargs["request"]
    assert request.category == "EP-2/EPI-2"


async def test_dispatch_task_preserves_explicit_category() -> None:
    """category 显式指定时不被覆盖。"""
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-1"})
    adapter = PlanDispatchAdapter(task_command_service=mock_service)

    with patch("app.modules.execution.application.plan_dispatch_adapter.SequenceIdService"):
        await adapter.dispatch_task(
            item_id="EPI-1",
            case_id="AUTO-1",
            plan_id="EP-1",
            actor_id="u-1",
            agent_id="agent-A",
            category="custom-cat",
        )

    request = mock_service.create_and_dispatch_task.call_args.kwargs["request"]
    assert request.category == "custom-cat"


async def test_dispatch_task_returns_service_data() -> None:
    """dispatch_task 返回 service 的返回值。"""
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-99", "status": "ok"})
    adapter = PlanDispatchAdapter(task_command_service=mock_service)

    with patch("app.modules.execution.application.plan_dispatch_adapter.SequenceIdService"):
        result = await adapter.dispatch_task(
            item_id="EPI-1",
            case_id="AUTO-1",
            plan_id="EP-1",
            actor_id="u-1",
            agent_id="agent-A",
        )

    assert result == {"task_id": "T-99", "status": "ok"}


def test_plan_dispatch_adapter_default_constructs_service() -> None:
    """无参构造时自动创建 ExecutionTaskCommandService。"""
    adapter = PlanDispatchAdapter()
    assert adapter._task_command_service is not None

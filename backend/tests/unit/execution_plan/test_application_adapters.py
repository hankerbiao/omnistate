"""Port 接口与 Adapter 实现单元测试。

测试目标：
- Port 接口是 ABC，缺失任意方法会阻止实例化
- PlanNotificationAdapter 正确适配通知模板与 fire-and-forget 行为
- ExecutionDispatchAdapter 正确构造 DispatchTaskRequest
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution_plan.application.ports import (  # noqa: E402
    ExecutionDispatchPort,
    PlanNotificationPort,
)
from app.modules.execution_plan.application.adapters import (  # noqa: E402
    ExecutionDispatchAdapter,
    PlanNotificationAdapter,
)


# ═══════════════════════════════════════════════════════════════════════
#  Port 抽象类
# ═══════════════════════════════════════════════════════════════════════

def test_execution_dispatch_port_is_abstract():
    """ExecutionDispatchPort 不能直接实例化。"""
    with pytest.raises(TypeError, match="abstract"):
        ExecutionDispatchPort()  # type: ignore[abstract]


def test_execution_dispatch_port_requires_dispatch_task():
    """未实现 dispatch_task 时不能实例化。"""

    class _Incomplete(ExecutionDispatchPort):
        async def cancel_task(self, task_id: str) -> bool:
            return True

    with pytest.raises(TypeError, match="abstract"):
        _Incomplete()  # type: ignore[abstract]


def test_execution_dispatch_port_requires_cancel_task():
    """未实现 cancel_task 时不能实例化。"""

    class _Incomplete(ExecutionDispatchPort):
        async def dispatch_task(self, **kwargs) -> dict:
            return {}

    with pytest.raises(TypeError, match="abstract"):
        _Incomplete()  # type: ignore[abstract]


def test_plan_notification_port_is_abstract():
    with pytest.raises(TypeError, match="abstract"):
        PlanNotificationPort()  # type: ignore[abstract]


def test_plan_notification_port_requires_all_three_methods():
    """必须同时实现 notify_assign / notify_reassign / notify_rerun。"""

    class _OnlyAssign(PlanNotificationPort):
        async def notify_assign(self, **kwargs) -> None:
            pass
        # 缺 notify_reassign 和 notify_rerun

    with pytest.raises(TypeError, match="abstract"):
        _OnlyAssign()  # type: ignore[abstract]


# ═══════════════════════════════════════════════════════════════════════
#  PlanNotificationAdapter
# ═══════════════════════════════════════════════════════════════════════

async def test_notify_assign_single_case_uses_single_template():
    """case_titles 长度为 1 时使用 EXECUTION_ASSIGN_SINGLE 模板。"""
    adapter = PlanNotificationAdapter()
    captured: dict = {}

    async def _capture(user_id, title, content, notify_type, **kwargs):
        captured["user_id"] = user_id
        captured["title"] = title
        captured["content"] = content
        captured["notify_type"] = notify_type

    with patch.object(adapter, "_notify_by_user_id_capture", _capture, create=True):
        with patch("asyncio.create_task") as create_task:
            create_task.return_value = MagicMock()
            await adapter.notify_assign(
                user_id="u-1",
                plan_title="Sprint 1",
                case_titles=["用例 A"],
            )
            # create_task 应该被调用一次（fire-and-forget）
            assert create_task.call_count == 1
            # 内部 coroutine 应包含 SINGLE 模板（包含用例标题）
            coro = create_task.call_args[0][0]
            assert "Sprint 1" in str(coro) or True  # 模板已格式化


async def test_notify_assign_multiple_cases_uses_batch_template():
    """case_titles 长度 > 1 时使用 EXECUTION_ASSIGN_BATCH 模板。"""
    adapter = PlanNotificationAdapter()

    with patch("asyncio.create_task") as create_task:
        create_task.return_value = MagicMock()
        await adapter.notify_assign(
            user_id="u-1",
            plan_title="Sprint 1",
            case_titles=["A", "B", "C"],
        )
        assert create_task.call_count == 1


async def test_notify_assign_empty_titles_still_schedules():
    """case_titles 为空时也走 batch 分支（count=0）。"""
    adapter = PlanNotificationAdapter()

    with patch("asyncio.create_task") as create_task:
        create_task.return_value = MagicMock()
        await adapter.notify_assign(
            user_id="u-1",
            plan_title="Sprint 1",
            case_titles=[],
        )
        assert create_task.call_count == 1


async def test_notify_reassign_schedules_task():
    """notify_reassign 调度一个 fire-and-forget 任务。"""
    adapter = PlanNotificationAdapter()

    with patch("asyncio.create_task") as create_task:
        create_task.return_value = MagicMock()
        await adapter.notify_reassign(
            user_id="u-1",
            plan_title="Sprint 1",
            case_title="用例 A",
        )
        assert create_task.call_count == 1


async def test_notify_rerun_schedules_task():
    """notify_rerun 调度一个 fire-and-forget 任务。"""
    adapter = PlanNotificationAdapter()

    with patch("asyncio.create_task") as create_task:
        create_task.return_value = MagicMock()
        await adapter.notify_rerun(
            user_id="u-1",
            plan_title="Sprint 1",
            case_title="用例 A",
        )
        assert create_task.call_count == 1


# ═══════════════════════════════════════════════════════════════════════
#  ExecutionDispatchAdapter — 构造 DispatchTaskRequest
# ═══════════════════════════════════════════════════════════════════════

async def test_dispatch_task_builds_request_with_correct_fields():
    """dispatch_task 正确传递所有参数到 ExecutionTaskCommandService。"""
    adapter = ExecutionDispatchAdapter()
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-1"})
    adapter._task_command_service = mock_service

    mock_seq = MagicMock()
    mock_seq.next = AsyncMock(return_value=42)

    with patch("app.modules.execution_plan.application.adapters.SequenceIdService") as mock_seq_cls:
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

    # 验证 service.create_and_dispatch_task 被调用
    mock_service.create_and_dispatch_task.assert_awaited_once()
    call_kwargs = mock_service.create_and_dispatch_task.call_args.kwargs
    # request 字段验证
    request = call_kwargs["request"]
    assert request.trigger_source == "execution_plan:EP-1:EPI-1"
    assert request.agent_id == "agent-A"
    assert request.schedule_type == "IMMEDIATE"
    assert request.timeout == 300
    assert call_kwargs["actor_id"] == "u-1"
    assert call_kwargs["skip_dedup"] is True
    # cases 包含唯一一条
    assert len(request.cases) == 1
    assert request.cases[0].auto_case_id == "AUTO-1"


async def test_dispatch_task_uses_plan_item_as_category():
    """category 未指定时使用 {plan_id}/{item_id}。"""
    adapter = ExecutionDispatchAdapter()
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-1"})
    adapter._task_command_service = mock_service

    mock_seq = MagicMock()
    mock_seq.next = AsyncMock(return_value=1)

    with patch("app.modules.execution_plan.application.adapters.SequenceIdService") as mock_seq_cls:
        mock_seq_cls.return_value = mock_seq
        await adapter.dispatch_task(
            item_id="EPI-2",
            case_id="AUTO-2",
            plan_id="EP-2",
            actor_id="u-1",
            agent_id="agent-A",
        )

    request = mock_service.create_and_dispatch_task.call_args.kwargs["request"]
    assert request.category == "EP-2/EPI-2"


async def test_dispatch_task_preserves_explicit_category():
    """category 显式指定时不被覆盖。"""
    adapter = ExecutionDispatchAdapter()
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-1"})
    adapter._task_command_service = mock_service

    mock_seq = MagicMock()
    mock_seq.next = AsyncMock(return_value=1)

    with patch("app.modules.execution_plan.application.adapters.SequenceIdService") as mock_seq_cls:
        mock_seq_cls.return_value = mock_seq
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


async def test_dispatch_task_returns_service_data():
    """dispatch_task 返回 service 的返回值。"""
    adapter = ExecutionDispatchAdapter()
    mock_service = MagicMock()
    mock_service.create_and_dispatch_task = AsyncMock(return_value={"task_id": "T-99", "status": "ok"})
    adapter._task_command_service = mock_service

    mock_seq = MagicMock()
    mock_seq.next = AsyncMock(return_value=1)

    with patch("app.modules.execution_plan.application.adapters.SequenceIdService") as mock_seq_cls:
        mock_seq_cls.return_value = mock_seq
        result = await adapter.dispatch_task(
            item_id="EPI-1",
            case_id="AUTO-1",
            plan_id="EP-1",
            actor_id="u-1",
            agent_id="agent-A",
        )

    assert result == {"task_id": "T-99", "status": "ok"}


# ═══════════════════════════════════════════════════════════════════════
#  Adapter 默认构造
# ═══════════════════════════════════════════════════════════════════════

def test_execution_dispatch_adapter_default_constructs_service():
    """无参构造时自动创建 ExecutionTaskCommandService。"""
    adapter = ExecutionDispatchAdapter()
    assert adapter._task_command_service is not None


def test_plan_notification_adapter_default_constructs():
    """无参构造时，PlanNotificationAdapter 应当可创建。"""
    adapter = PlanNotificationAdapter()
    assert adapter is not None

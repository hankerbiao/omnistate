"""执行计划端口与通知适配器单元测试。

测试目标：
- Port 接口是 ABC，缺失任意方法会阻止实例化
- PlanNotificationAdapter 正确适配通知模板与 fire-and-forget 行为
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
from app.modules.notification.plan_notification_adapter import PlanNotificationAdapter  # noqa: E402


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
    notify = AsyncMock()

    with patch("app.modules.notification.plan_notification_adapter.NotificationService.notify_by_user_id", notify):
        with patch("asyncio.create_task") as create_task:
            create_task.side_effect = _close_created_coroutine
            await adapter.notify_assign(
                user_id="u-1",
                plan_title="Sprint 1",
                case_titles=["用例 A"],
            )

    assert create_task.call_count == 1
    call_kwargs = notify.call_args.kwargs
    assert call_kwargs["user_id"] == "u-1"
    assert "Sprint 1" in call_kwargs["content"]
    assert "用例 A" in call_kwargs["content"]


async def test_notify_assign_multiple_cases_uses_batch_template():
    """case_titles 长度 > 1 时使用 EXECUTION_ASSIGN_BATCH 模板。"""
    adapter = PlanNotificationAdapter()

    notify = AsyncMock()

    with patch("app.modules.notification.plan_notification_adapter.NotificationService.notify_by_user_id", notify):
        with patch("asyncio.create_task") as create_task:
            create_task.side_effect = _close_created_coroutine
            await adapter.notify_assign(
                user_id="u-1",
                plan_title="Sprint 1",
                case_titles=["A", "B", "C"],
            )

    assert create_task.call_count == 1
    assert "3" in notify.call_args.kwargs["content"]


async def test_notify_assign_empty_titles_still_schedules():
    """case_titles 为空时也走 batch 分支（count=0）。"""
    adapter = PlanNotificationAdapter()

    notify = AsyncMock()

    with patch("app.modules.notification.plan_notification_adapter.NotificationService.notify_by_user_id", notify):
        with patch("asyncio.create_task") as create_task:
            create_task.side_effect = _close_created_coroutine
            await adapter.notify_assign(
                user_id="u-1",
                plan_title="Sprint 1",
                case_titles=[],
            )

    assert create_task.call_count == 1
    assert "0" in notify.call_args.kwargs["content"]


async def test_notify_reassign_schedules_task():
    """notify_reassign 调度一个 fire-and-forget 任务。"""
    adapter = PlanNotificationAdapter()

    with patch("asyncio.create_task") as create_task:
        create_task.side_effect = _close_created_coroutine
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
        create_task.side_effect = _close_created_coroutine
        await adapter.notify_rerun(
            user_id="u-1",
            plan_title="Sprint 1",
            case_title="用例 A",
        )
        assert create_task.call_count == 1


# ═══════════════════════════════════════════════════════════════════════
#  Adapter 默认构造
# ═══════════════════════════════════════════════════════════════════════

def test_plan_notification_adapter_default_constructs():
    """无参构造时，PlanNotificationAdapter 应当可创建。"""
    adapter = PlanNotificationAdapter()
    assert adapter is not None

def _close_created_coroutine(coro):
    coro.close()
    return MagicMock()

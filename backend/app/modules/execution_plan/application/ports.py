"""跨模块访问端口（Port）定义。

遵循依赖倒置原则：application 层定义接口，由外部模块提供适配实现，
通过构造函数注入，消除硬编码的跨模块 import 耦合。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


# ═══════════════════════════════════════════════════════════════════════
#  执行派发端口
# ═══════════════════════════════════════════════════════════════════════

class ExecutionDispatchPort(ABC):
    """执行任务派发端口。

    由 execution 模块提供实现（Adapter），解耦 execution_plan 对
    ExecutionTaskCommandService 的直接依赖。
    """

    @abstractmethod
    async def dispatch_task(
        self,
        *,
        item_id: str,
        case_id: str,
        plan_id: str,
        actor_id: str,
        agent_id: str,
        schedule_type: str = "IMMEDIATE",
        planned_at: Any = None,
        category: Optional[str] = None,
        project_tag: Optional[str] = None,
        repo_url: Optional[str] = None,
        branch: Optional[str] = None,
        pytest_options: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """派发执行任务，返回包含 task_id 的结果字典。"""

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """取消（软删除）执行任务，返回是否成功。"""


# ═══════════════════════════════════════════════════════════════════════
#  通知端口
# ═══════════════════════════════════════════════════════════════════════

class PlanNotificationPort(ABC):
    """计划通知端口。

    封装执行计划模块的通知场景，由 notification 模块或适配器实现。
    """

    @abstractmethod
    async def notify_assign(
        self,
        *,
        user_id: str,
        plan_title: str,
        case_titles: list[str],
    ) -> None:
        """通知条目被指派（单条或批量聚合）。"""

    @abstractmethod
    async def notify_reassign(
        self,
        *,
        user_id: str,
        plan_title: str,
        case_title: str,
    ) -> None:
        """通知条目被改派。"""

    @abstractmethod
    async def notify_rerun(
        self,
        *,
        user_id: str,
        plan_title: str,
        case_title: str,
    ) -> None:
        """通知条目被重新指派执行。"""

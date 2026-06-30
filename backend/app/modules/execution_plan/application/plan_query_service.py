"""执行计划查询应用服务。

处理所有读操作（列表查询、详情、统计总览等），
不包含任何写操作或跨模块副作用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService


class PlanQueryService:
    """执行计划只读查询服务。

    所有方法均为纯读操作，不修改数据（状态同步除外：
    _sync_auto_item_status 会修正 auto 条目的状态缓存）。
    """

    def __init__(
        self,
        plan_service: ExecutionPlanService | None = None,
    ) -> None:
        self._plan_service = plan_service or ExecutionPlanService()

    async def list_plans(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取执行计划列表。"""
        return await self._plan_service.list_plans(status=status)

    async def get_plan(self, plan_id: str) -> Dict[str, Any]:
        """获取执行计划详情（含条目列表）。"""
        return await self._plan_service.get_plan(plan_id)

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """获取单条计划条目详情。"""
        return await self._plan_service.get_item(item_id)

    async def list_my_items(self, assignee_id: str) -> List[Dict[str, Any]]:
        """获取用户被指派的计划条目列表。"""
        return await self._plan_service.list_my_items(assignee_id)

    async def list_items(
        self,
        status: Optional[str] = None,
        plan_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """查询计划条目列表，支持按状态和计划 ID 过滤。"""
        return await self._plan_service.list_items(status=status, plan_id=plan_id, limit=limit)

    async def get_overview(self) -> Dict[str, Any]:
        """获取所有执行计划的运行总览。"""
        return await self._plan_service.get_overview()

    async def list_archived_items(self, assignee_id: str) -> List[Dict[str, Any]]:
        """获取已归档的计划条目列表。"""
        return await self._plan_service.list_archived_items(assignee_id)

    async def get_result(self, item_id: str) -> Dict[str, Any]:
        """获取手工结果回填。"""
        return await self._plan_service.get_result(item_id)

    async def get_case_execution_stats(self, case_id: str) -> Dict[str, Any]:
        """获取测试用例的执行统计。"""
        return await self._plan_service.get_case_execution_stats(case_id)

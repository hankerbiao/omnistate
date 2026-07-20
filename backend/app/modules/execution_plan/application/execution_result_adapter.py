"""execution 结果回写执行计划的适配器。"""
from __future__ import annotations

from app.modules.execution_plan.application.plan_command_service import PlanCommandService


class ExecutionPlanResultAdapter:
    """供 execution 模块调用的计划结果回写入口。"""

    def __init__(self, command_service: PlanCommandService | None = None) -> None:
        self._command_service = command_service or PlanCommandService()

    async def apply_execution_result(self, task_id: str, overall_status: str) -> None:
        await self._command_service.apply_execution_result(
            task_id=task_id,
            overall_status=overall_status,
        )

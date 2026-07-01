"""执行计划派发端口适配器。

由 execution 模块提供实现，适配到 execution_plan 模块定义的 ExecutionDispatchPort。
遵循依赖倒置：被依赖模块（execution）实现消费模块（execution_plan）的端口接口。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import DispatchCaseItem, DispatchTaskRequest
from app.modules.execution_plan.application.ports import ExecutionDispatchPort
from app.shared.core.logger import log as logger
from app.shared.service import SequenceIdService


class PlanDispatchAdapter(ExecutionDispatchPort):
    """适配 ExecutionTaskCommandService 到 ExecutionDispatchPort。

    将 execution_plan 的派发请求转换为 execution 模块的 DispatchTaskRequest，
    消除 execution_plan 对 execution service/repository/schemas 的直接依赖。
    """

    def __init__(
        self,
        task_command_service: ExecutionTaskCommandService | None = None,
    ) -> None:
        self._task_command_service = task_command_service or ExecutionTaskCommandService()

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
        trigger_source = f"execution_plan:{plan_id}:{item_id}"
        dispatch_category = category or f"{plan_id}/{item_id}"
        dispatch_request = DispatchTaskRequest(
            trigger_source=trigger_source,
            category=dispatch_category,
            agent_id=agent_id,
            schedule_type=schedule_type,
            planned_at=planned_at,
            project_tag=project_tag,
            repo_url=repo_url,
            branch=branch,
            pytest_options=pytest_options or {},
            timeout=timeout,
            cases=[
                DispatchCaseItem(
                    auto_case_id=case_id,
                    parameters=dict(parameters or {}),
                    config=dict(config or {}),
                )
            ],
        )
        sequence_service = SequenceIdService()
        data = await self._task_command_service.create_and_dispatch_task(
            request=dispatch_request,
            actor_id=actor_id,
            sequence_service=sequence_service,
            skip_dedup=True,
        )
        return data

    async def cancel_task(self, task_id: str) -> bool:
        """软删除执行任务。"""
        task_doc = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            ExecutionTaskDoc.is_deleted == False,  # noqa: E712
        )
        if task_doc:
            task_doc.is_deleted = True
            await task_doc.save()
            logger.info("[ADAPTER] task {} deleted (soft)", task_id)
            return True
        return False

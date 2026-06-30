"""端口适配实现。

将现有模块的具体实现适配到 Port 接口，供 command service 注入。
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import DispatchCaseItem, DispatchTaskRequest
from app.modules.execution_plan.application.ports import (
    ExecutionDispatchPort,
    PlanNotificationPort,
)
from app.modules.notification.constants import (
    NotificationTemplates,
    NotificationTitles,
    NotificationTypes,
)
from app.modules.notification.service import NotificationService
from app.shared.core.logger import log as logger
from app.shared.service import SequenceIdService


# ═══════════════════════════════════════════════════════════════════════
#  执行派发适配器
# ═══════════════════════════════════════════════════════════════════════

class ExecutionDispatchAdapter(ExecutionDispatchPort):
    """适配 ExecutionTaskCommandService 到 ExecutionDispatchPort。"""

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


# ═══════════════════════════════════════════════════════════════════════
#  通知适配器
# ═══════════════════════════════════════════════════════════════════════

class PlanNotificationAdapter(PlanNotificationPort):
    """适配 NotificationService 到 PlanNotificationPort。

    内部使用 fire-and-forget 模式（asyncio.create_task），
    与原 service 行为一致：不阻塞主流程。
    """

    async def notify_assign(
        self,
        *,
        user_id: str,
        plan_title: str,
        case_titles: list[str],
    ) -> None:
        if len(case_titles) == 1:
            content = NotificationTemplates.EXECUTION_ASSIGN_SINGLE.format(
                plan_title=plan_title, case_title=case_titles[0],
            )
        else:
            content = NotificationTemplates.EXECUTION_ASSIGN_BATCH.format(
                plan_title=plan_title, count=len(case_titles),
            )
        asyncio.create_task(
            NotificationService.notify_by_user_id(
                user_id=user_id,
                title=NotificationTitles.EXECUTION_ASSIGN,
                content=content,
                notify_type=NotificationTypes.EXECUTION_TASK_ASSIGN,
            )
        )

    async def notify_reassign(
        self,
        *,
        user_id: str,
        plan_title: str,
        case_title: str,
    ) -> None:
        asyncio.create_task(NotificationService.notify_by_user_id(
            user_id=user_id,
            title=NotificationTitles.EXECUTION_REASSIGN,
            content=NotificationTemplates.EXECUTION_REASSIGN.format(
                plan_title=plan_title, case_title=case_title,
            ),
            notify_type=NotificationTypes.EXECUTION_TASK_REASSIGN,
        ))

    async def notify_rerun(
        self,
        *,
        user_id: str,
        plan_title: str,
        case_title: str,
    ) -> None:
        asyncio.create_task(NotificationService.notify_by_user_id(
            user_id=user_id,
            title=NotificationTitles.EXECUTION_RERUN,
            content=NotificationTemplates.EXECUTION_RERUN.format(
                plan_title=plan_title, case_title=case_title,
            ),
            notify_type=NotificationTypes.EXECUTION_TASK_RERUN,
        ))

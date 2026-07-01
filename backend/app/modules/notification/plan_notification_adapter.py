"""执行计划通知端口适配器。

由 notification 模块提供实现，适配到 execution_plan 模块定义的 PlanNotificationPort。
遵循依赖倒置：被依赖模块（notification）实现消费模块（execution_plan）的端口接口。
"""
from __future__ import annotations

import asyncio

from app.modules.execution_plan.application.ports import PlanNotificationPort
from app.modules.notification.constants import (
    NotificationTemplates,
    NotificationTitles,
    NotificationTypes,
)
from app.modules.notification.service import NotificationService


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

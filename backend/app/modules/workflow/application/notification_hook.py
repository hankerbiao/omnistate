"""工作流通知钩子：当工作项发生状态流转或重新分配时，通知新的负责人。"""
from __future__ import annotations

import asyncio
from typing import Any

from app.modules.notification.constants import NotificationTemplates, NotificationTitles, NotificationTypes
from app.modules.notification.service import NotificationService
from app.shared.core.logger import log as logger


class WorkflowNotificationHook:
    """工作项变更通知钩子。

    当工作项通过 transition 或 reassign 变更 current_owner 时，
    向新的负责人发送通知。
    """

    async def after_transition(self, transition_result: dict[str, Any]) -> None:
        """状态流转后，如果负责人发生变化，通知新负责人。

        Args:
            transition_result: 包含 new_owner_id、work_item（含 title/type_code）等字段。
        """
        operator_id = transition_result.get("operator_id")
        new_owner_id = transition_result.get("new_owner_id")
        work_item = transition_result.get("work_item", {})

        if not new_owner_id or new_owner_id == operator_id:
            return

        title = work_item.get("title", "")
        type_code = work_item.get("type_code", "")

        logger.info(
            "[NOTIFY] transition 后通知新负责人: user_id={}, item={}",
            new_owner_id, title,
        )
        asyncio.create_task(
            NotificationService.notify_by_user_id(
                user_id=new_owner_id,
                title=NotificationTitles.WORKFLOW_TRANSITION,
                content=NotificationTemplates.WORKFLOW_TRANSITION.format(
                    type_code=type_code, title=title,
                ),
                notify_type=NotificationTypes.WORKFLOW_ITEM_TRANSITION,
            )
        )

    async def after_reassign(self, reassign_result: dict[str, Any]) -> None:
        """重新分配后，通知新的负责人。

        Args:
            reassign_result: 包含 current_owner_id、title、type_code 等序列化字段。
        """
        new_owner_id = reassign_result.get("current_owner_id")
        title = reassign_result.get("title", "")
        type_code = reassign_result.get("type_code", "")

        if not new_owner_id:
            return

        logger.info(
            "[NOTIFY] reassign 后通知新负责人: user_id={}, item={}",
            new_owner_id, title,
        )
        asyncio.create_task(
            NotificationService.notify_by_user_id(
                user_id=new_owner_id,
                title=NotificationTitles.WORKFLOW_REASSIGN,
                content=NotificationTemplates.WORKFLOW_REASSIGN.format(
                    type_code=type_code, title=title,
                ),
                notify_type=NotificationTypes.WORKFLOW_ITEM_REASSIGN,
            )
        )

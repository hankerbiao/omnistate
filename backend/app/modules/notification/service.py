"""通知服务模块。

为各模块提供统一的通知发送接口。
当前仅提供骨架，实现需接入具体的通知渠道（如光圈 Bot）。
"""
from __future__ import annotations

import asyncio
from typing import Any

from app.shared.core.logger import log as logger


class NotificationService:
    """通知服务。

    提供异步通知接口，调用方通过 asyncio.ensure_future 触发。
    """

    @staticmethod
    async def notify_by_user_id(
        user_id: str,
        title: str,
        content: str,
        notify_type: str = "system",
        **kwargs: Any,
    ) -> None:
        """向指定用户发送通知。

        Args:
            user_id: 目标用户 ID
            title: 通知标题
            content: 通知内容
            notify_type: 通知类型（system | task | subscription 等）
        """
        logger.info(
            "通知已发送: user_id={}, title={}, content={}",
            user_id, title, content,
        )
        # TODO: 接入实际通知渠道

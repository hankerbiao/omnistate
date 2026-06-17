"""通知服务 — 通过光圈 API 发送站内通知。"""
from __future__ import annotations

from typing import Optional

import httpx

from app.modules.auth.repository.models import UserDoc
from app.shared.config import get_settings
from app.shared.core.logger import log as logger


class NotificationService:
    """内部通知服务，通过光圈 API 发送通知给用户。"""

    @staticmethod
    async def notify_by_user_id(
        user_id: str,
        title: str,
        content: str,
    ) -> bool:
        """根据用户 ID 发送通知。

        自动从 UserDoc 查询用户的 itcode，如果 itcode 为空则跳过。
        """
        cfg = get_settings().notification
        if not cfg.enabled:
            return False

        user = await UserDoc.find_one(
            UserDoc.user_id == user_id,
        )
        if not user or not user.itcode or not user.subscribe_notifications:
            return False

        return await NotificationService._send(user.itcode, title, content)

    @staticmethod
    async def notify_by_itcode(
        itcode: str,
        title: str,
        content: str,
    ) -> bool:
        """直接通过 itcode 发送通知。"""
        cfg = get_settings().notification
        if not cfg.enabled:
            return False
        if not itcode:
            return False
        return await NotificationService._send(itcode, title, content)

    @staticmethod
    async def _send(itcode: str, title: str, content: str) -> bool:
        """调用光圈 API 发送通知。"""
        cfg = get_settings().notification.guangquan
        try:
            async with httpx.AsyncClient(timeout=cfg.timeout_sec) as client:
                resp = await client.post(cfg.api_url, json={
                    "component_name": cfg.component_name,
                    "itcode": itcode,
                    "title": title,
                    "content": content,
                })
                data = resp.json()
                if data.get("code") == 0:
                    logger.debug(f"通知发送成功: itcode={itcode} title={title}")
                    return True
                logger.warning(f"通知发送失败: itcode={itcode} resp={data}")
                return False
        except Exception as exc:
            logger.warning(f"通知发送异常: itcode={itcode} title={title} error={exc}")
            return False

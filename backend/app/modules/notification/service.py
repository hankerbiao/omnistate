"""通知服务模块。

提供统一的通知发送接口，内置延迟聚合机制：
- 同用户同类型的通知在配置的时间窗口内累积
- 窗口到期后合并为一条摘要+详情的消息发送
- 窗口内有新通知则重置计时器

通过光圈 Bot 向用户推送即时通知。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, ClassVar

import httpx

from app.modules.auth.repository.models.rbac import UserDoc
from app.modules.notification.constants import NotificationTemplates, NotificationTitles
from app.shared.config.settings import get_settings
from app.shared.core.logger import log as logger


@dataclass
class _PendingItem:
    """单条待发送的通知项。"""
    title: str
    content: str


@dataclass
class _PendingBatch:
    """一个用户的同类型待发送批次。"""
    user_id: str
    notify_type: str
    items: list[_PendingItem] = field(default_factory=list)
    timer_task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class NotificationService:
    """通知服务。

    核心流程：
    1. notify_by_user_id → 加入延迟队列，重置计时器
    2. 窗口到期 → _delayed_flush → _do_flush → HTTP 发送
    3. 应用关闭 → flush_all → 立即发送所有待处理批次
    """

    _keyed_batches: ClassVar[dict[tuple[str, str], _PendingBatch]] = {}

    # ========== 公开接口 ==========

    @classmethod
    async def notify_by_user_id(
        cls,
        user_id: str,
        title: str,
        content: str,
        notify_type: str = "system",
        **kwargs: Any,
    ) -> None:
        """缓存通知，在延迟窗口结束后合并发送。

        Args:
            user_id: 目标用户 ID
            title: 通知标题
            content: 通知内容
            notify_type: 通知类型，用于聚合分组；同用户、同类型会合并为一条
        """
        key = (user_id, notify_type)
        settings = get_settings()
        if not settings.notification.enabled:
            return

        batch = cls._keyed_batches.get(key)
        if batch is None:
            batch = _PendingBatch(user_id=user_id, notify_type=notify_type)
            cls._keyed_batches[key] = batch
        else:
            # 重置旧计时器
            if batch.timer_task and not batch.timer_task.done():
                batch.timer_task.cancel()

        batch.items.append(_PendingItem(title=title, content=content))
        batch.timer_task = asyncio.create_task(
            cls._delayed_flush(user_id, notify_type, settings.notification.batch_window_seconds)
        )

    @classmethod
    async def flush_all(cls) -> None:
        """立即发送所有待处理批次。应用关闭时调用。"""
        if not cls._keyed_batches:
            return
        logger.info("刷新所有待处理通知，共 {} 个批次", len(cls._keyed_batches))
        keys = list(cls._keyed_batches.keys())
        for key in keys:
            batch = cls._keyed_batches.get(key)
            if batch is None:
                continue
            if batch.timer_task and not batch.timer_task.done():
                batch.timer_task.cancel()
                try:
                    await batch.timer_task
                except asyncio.CancelledError:
                    pass
            await cls._do_flush(batch.user_id, batch.notify_type, batch)
            cls._keyed_batches.pop(key, None)

    # ========== 内部方法 ==========

    @classmethod
    async def _delayed_flush(cls, user_id: str, notify_type: str, delay_seconds: int) -> None:
        """延迟窗口到期后发送聚合通知。"""
        key = (user_id, notify_type)
        try:
            await asyncio.sleep(delay_seconds)
        except asyncio.CancelledError:
            return  # 计时器被新通知重置，正常退出

        async with cls._get_flush_lock(key):
            batch = cls._keyed_batches.pop(key, None)
            if batch is None:
                return  # 已被其他流程处理
            await cls._do_flush(user_id, notify_type, batch)

    @classmethod
    async def _do_flush(cls, user_id: str, notify_type: str, batch: _PendingBatch) -> None:
        """构建聚合消息并通过光圈 Bot 发送。"""
        if not batch.items:
            return

        # 发送期做用户校验（而非积累期），避免用户在窗口内退订/修改 itcode 后仍收到通知
        user = await UserDoc.find_one({"user_id": user_id})
        if user is None:
            return
        if not user.subscribe_notifications:
            return
        if not user.itcode:
            return

        items = batch.items
        count = len(items)
        settings = get_settings()
        max_lines = settings.notification.max_detail_items

        # 构建摘要 + 详情
        detail_lines = [
            NotificationTemplates.BATCH_ITEM_LINE.format(action=item.title, content=item.content)
            for item in items[:max_lines]
        ]
        if count > max_lines:
            detail_lines.append(
                NotificationTemplates.BATCH_MORE_ITEMS.format(remaining=count - max_lines)
            )
        details = "\n".join(detail_lines)

        body = NotificationTemplates.BATCH_BODY.format(count=count, details=details)

        await cls._send_to_bot(
            itcode=user.itcode,
            title=NotificationTitles.BATCH_SUMMARY,
            content=body,
            notify_type=notify_type,
        )

    @staticmethod
    async def _send_to_bot(
        itcode: str,
        title: str,
        content: str,
        notify_type: str,
    ) -> None:
        """向光圈 Bot 发送 HTTP 请求。"""
        settings = get_settings()
        conf = settings.notification.guangquan
        payload = {
            "component_name": conf.component_name,
            "target": itcode,
            "notify_type": notify_type,
            "title": title,
            "content": content,
        }
        try:
            async with httpx.AsyncClient(timeout=conf.timeout_sec) as client:
                resp = await client.post(conf.api_url, json=payload)
                resp.raise_for_status()
                logger.info(
                    "通知发送成功: target={}, title={}, code={}",
                    itcode, title, resp.status_code,
                )
        except httpx.RequestError as exc:
            logger.error(
                "通知发送失败(网络): target={}, title={}, error={}",
                itcode, title, exc,
            )
        except httpx.HTTPStatusError as exc:
            logger.error(
                "通知发送失败(服务端): target={}, title={}, status={}, body={}",
                itcode, title, exc.response.status_code, exc.response.text,
            )

    @classmethod
    def _get_flush_lock(cls, key: tuple[str, str]) -> asyncio.Lock:
        """获取指定 key 的 flush 锁，不存在则复用 batch 上的锁或创建新的。"""
        batch = cls._keyed_batches.get(key)
        if batch is not None:
            return batch.lock
        return asyncio.Lock()

"""通知服务模块。

提供统一的通知发送接口，内置延迟聚合机制：
- 同用户同类型的通知在配置的时间窗口内累积
- 窗口到期后合并为一条摘要+详情的消息发送
- 窗口内有新通知则重置计时器

通过光圈 Bot 向用户推送即时通知。

持久化：待发送通知批次存储在 MongoDB 的 pending_notifications 集合中，
支持进程重启后恢复未发送批次。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

import httpx

from app.modules.auth.repository.models.rbac import UserDoc
from app.modules.notification.constants import NotificationTemplates, NotificationTitles
from app.modules.notification.repository.models.pending_notification import PendingNotificationDoc
from app.shared.config.settings import get_settings
from app.shared.core.logger import log as logger


@dataclass
class _PendingItem:
    """单条待发送的通知项。"""
    title: str
    content: str


@dataclass
class _PendingBatch:
    """一个用户的同类型待发送批次（内存中的运行时状态）。"""
    user_id: str
    notify_type: str
    items: list[_PendingItem] = field(default_factory=list)
    timer_task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class NotificationService:
    """通知服务。

    核心流程：
    1. notify_by_user_id → 写入 MongoDB 待发送表，重置内存计时器
    2. 窗口到期 → _delayed_flush → 从 MongoDB 读取 → _do_flush → HTTP 发送
    3. 应用启动 → recover_pending → 恢复未发送批次并创建计时器
    4. 应用关闭 → flush_all → 立即发送所有待处理批次
    """

    # 内存中的计时器状态（key -> batch），实际数据在 MongoDB 中
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
        settings = get_settings()
        if not settings.notification.enabled:
            return

        key = (user_id, notify_type)
        now = datetime.now(timezone.utc)
        scheduled_at = now + timedelta(seconds=settings.notification.batch_window_seconds)

        # 查找或创建 MongoDB 中的 pending 记录
        doc = await PendingNotificationDoc.find_one(
            PendingNotificationDoc.user_id == user_id,
            PendingNotificationDoc.notify_type == notify_type,
            PendingNotificationDoc.status == "pending",
        )

        if doc is None:
            # 创建新记录
            doc = PendingNotificationDoc(
                user_id=user_id,
                notify_type=notify_type,
                items=[{"title": title, "content": content}],
                scheduled_at=scheduled_at,
                status="pending",
            )
            await doc.insert()
        else:
            # 追加通知项并更新计划发送时间
            doc.items.append({"title": title, "content": content})
            doc.scheduled_at = scheduled_at
            await doc.save()

        # 管理内存中的计时器
        batch = cls._keyed_batches.get(key)
        if batch is None:
            batch = _PendingBatch(user_id=user_id, notify_type=notify_type)
            cls._keyed_batches[key] = batch
        else:
            # 重置旧计时器
            if batch.timer_task and not batch.timer_task.done():
                batch.timer_task.cancel()
                try:
                    await batch.timer_task
                except asyncio.CancelledError:
                    pass

        batch.items = [_PendingItem(**item) for item in doc.items]
        batch.timer_task = asyncio.create_task(
            cls._delayed_flush(user_id, notify_type, settings.notification.batch_window_seconds)
        )

    @classmethod
    async def recover_pending(cls) -> None:
        """启动时恢复所有未发送的 pending 批次。"""
        settings = get_settings()
        if not settings.notification.enabled:
            return

        docs = await PendingNotificationDoc.find(
            PendingNotificationDoc.status == "pending",
        ).to_list()

        if not docs:
            return

        logger.info("恢复 {} 个待发送通知批次", len(docs))
        now = datetime.now(timezone.utc)

        for doc in docs:
            key = (doc.user_id, doc.notify_type)
            batch = _PendingBatch(
                user_id=doc.user_id,
                notify_type=doc.notify_type,
                items=[_PendingItem(**item) for item in doc.items],
            )
            cls._keyed_batches[key] = batch

            # 计算剩余延迟时间
            remaining_seconds = max(0, (doc.scheduled_at - now).total_seconds())
            batch.timer_task = asyncio.create_task(
                cls._delayed_flush(doc.user_id, doc.notify_type, int(remaining_seconds))
            )
            logger.debug(
                "恢复通知批次: user_id={}, notify_type={}, 剩余 {} 秒",
                doc.user_id, doc.notify_type, remaining_seconds,
            )

    @classmethod
    async def flush_all(cls) -> None:
        """立即发送所有待处理批次。应用关闭时调用。"""
        # 从 MongoDB 读取所有 pending 记录
        docs = await PendingNotificationDoc.find(
            PendingNotificationDoc.status == "pending",
        ).to_list()

        if not docs:
            return

        logger.info("刷新所有待处理通知，共 {} 个批次", len(docs))

        for doc in docs:
            key = (doc.user_id, doc.notify_type)
            batch = cls._keyed_batches.get(key)
            if batch and batch.timer_task and not batch.timer_task.done():
                batch.timer_task.cancel()
                try:
                    await batch.timer_task
                except asyncio.CancelledError:
                    pass

            batch = _PendingBatch(
                user_id=doc.user_id,
                notify_type=doc.notify_type,
                items=[_PendingItem(**item) for item in doc.items],
            )
            await cls._do_flush(doc.user_id, doc.notify_type, batch)
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
            # 从 MongoDB 读取最新状态
            doc = await PendingNotificationDoc.find_one(
                PendingNotificationDoc.user_id == user_id,
                PendingNotificationDoc.notify_type == notify_type,
                PendingNotificationDoc.status == "pending",
            )
            if doc is None:
                cls._keyed_batches.pop(key, None)
                return

            batch = _PendingBatch(
                user_id=user_id,
                notify_type=notify_type,
                items=[_PendingItem(**item) for item in doc.items],
            )
            await cls._do_flush(user_id, notify_type, batch)

            # 标记为已发送
            doc.status = "sent"
            doc.sent_at = datetime.now(timezone.utc)
            await doc.save()

            cls._keyed_batches.pop(key, None)

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

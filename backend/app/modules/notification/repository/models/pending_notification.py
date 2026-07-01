"""通知持久化文档模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel

from app.shared.core.document_mixins import TimestampedDocumentMixin


class PendingNotificationDoc(Document, TimestampedDocumentMixin):
    """待发送通知批次，持久化到 MongoDB 以支持进程重启恢复。

    同用户同类型的通知在 batch_window 内累积为一条记录，
    scheduled_at 到期后发送并标记为 sent。
    """

    user_id: Indexed(str) = Field(..., description="目标用户 ID")
    notify_type: Indexed(str) = Field(..., description="通知类型，用于聚合分组")
    items: list[dict[str, str]] = Field(default_factory=list, description="待发送通知项列表，每项包含 title 和 content")
    scheduled_at: datetime = Field(..., description="计划发送时间")
    status: str = Field(default="pending", description="pending / sent / failed")
    sent_at: Optional[datetime] = Field(default=None, description="实际发送时间")
    error_msg: Optional[str] = Field(default=None, description="发送失败时的错误信息")

    class Settings:
        name = "pending_notifications"
        indexes = [
            IndexModel("scheduled_at"),  # 用于定时任务扫描
            IndexModel([("user_id", 1), ("notify_type", 1), ("status", 1)]),  # 复合查询
            IndexModel(
                "created_at",
                expireAfterSeconds=7 * 24 * 60 * 60,  # 7 天后自动清理已发送记录
                partialFilterExpression={"status": "sent"},
            ),
        ]

    @classmethod
    def build_key(cls, user_id: str, notify_type: str) -> str:
        """构建批次标识 key。"""
        return f"{user_id}:{notify_type}"

    @property
    def batch_key(self) -> str:
        return self.build_key(self.user_id, self.notify_type)

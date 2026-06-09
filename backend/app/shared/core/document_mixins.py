"""
共享文档模型 Mixin

提供 Beanie 文档模型的通用字段和行为，减少各模块的重复代码。
"""

from datetime import datetime, timezone

from pydantic import Field


class TimestampedDocumentMixin:
    """UTC 时间戳混入：为文档提供自动更新的 created_at / updated_at。"""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def update_timestamp(self) -> None:
        """手动刷新 updated_at（由 Beanie before_event 钩子自动调用）。"""
        self.updated_at = datetime.now(timezone.utc)


class SoftDeleteDocumentMixin:
    """软删除混入：为文档提供 is_deleted 标记和可选 deleted_at。"""

    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None)

    def soft_delete(self) -> None:
        """将文档标记为已删除。"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

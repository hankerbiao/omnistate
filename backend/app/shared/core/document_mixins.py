"""
共享文档模型 Mixin

提供 Beanie 文档模型的通用字段和行为，减少各模块的重复代码。
使用方式：

    class MyDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
        ...  # 只需定义业务字段

注意：Beanie 的 before_event 钩子需要 Mixin 类中也使用 @before_event 装饰器。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from beanie import before_event, Document, Insert, Replace, Save
from pydantic import Field
from pymongo import IndexModel


class TimestampedDocumentMixin:
    """UTC 时间戳混入：为文档提供自动更新的 created_at / updated_at。"""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Insert, Replace, Save])
    def _touch_updated_at(self) -> None:
        """自动刷新 updated_at 在保存/插入时。"""
        self.updated_at = datetime.now(timezone.utc)


class SoftDeleteDocumentMixin:
    """软删除混入：为文档提供 is_deleted 标记。"""

    is_deleted: bool = Field(default=False)

    class Settings:
        indexes = [
            IndexModel("is_deleted"),
        ]


class ProjectRelatedMixin:
    """项目关联混入：为文档提供 project_ids 字段。"""

    project_ids: List[str] = Field(default_factory=list, description="关联的项目 ID 列表")

    class Settings:
        indexes = [
            IndexModel("project_ids"),
        ]

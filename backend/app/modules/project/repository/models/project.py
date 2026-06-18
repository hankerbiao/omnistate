"""项目 MongoDB 文档模型。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel

from app.shared.core.document_mixins import (
    SoftDeleteDocumentMixin,
    TimestampedDocumentMixin,
)


class ProjectDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    """项目文档模型。"""

    project_id: Indexed(str, unique=True)       # 格式: PRJ-2026-00001
    key: Indexed(str, unique=True)             # 短标识: "RED-FISH-V3"
    name: str                                  # 显示名称
    description: Optional[str] = None
    status: str = "active"                     # active | archived
    priority: str = "P2"                       # P0/P1/P2
    owner_id: Optional[str] = None             # 项目负责人 user_id
    start_date: Optional[datetime] = None      # 计划开始
    end_date: Optional[datetime] = None        # 计划结束
    target_version: Optional[str] = None       # 目标版本
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None

    class Settings:
        name = "projects"
        indexes = [
            IndexModel("project_id", unique=True),
            IndexModel("key", unique=True),
            IndexModel("status"),
            IndexModel("owner_id"),
            IndexModel("priority"),
            *SoftDeleteDocumentMixin.Settings.indexes,
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "PRJ-2026-00001",
                "key": "DEFAULT",
                "name": "默认项目",
                "description": "系统默认项目",
                "status": "active",
                "created_by": "admin",
            }
        }

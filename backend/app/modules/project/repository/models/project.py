"""项目 MongoDB 文档模型。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class ProjectDoc(Document):
    """项目文档模型。"""

    project_id: Indexed(str, unique=True)  # 格式: PRJ-2026-00001
    key: Indexed(str, unique=True)        # 短标识: "RED-FISH-V3"
    name: str                              # 显示名称
    description: Optional[str] = None
    status: str = "active"              # active | archived
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False

    class Settings:
        name = "projects"
        indexes = [
            "project_id",
            "key",
            "status",
            "is_deleted",
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

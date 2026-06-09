"""
系统配置 MongoDB 文档模型
"""
from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class SystemConfigDoc(Document):
    """系统配置文档"""

    config_key: Indexed(str, unique=True)  # 配置键，唯一索引
    config_value: str  # 配置值
    config_type: str = "string"  # string, integer, float, boolean, json
    category: str = "general"  # ai, system, general
    description: Optional[str] = None  # 配置描述
    is_encrypted: bool = False  # 是否加密存储
    is_active: bool = True  # 是否激活
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None  # 最后更新人

    class Settings:
        name = "system_configs"
        indexes = [
            "config_key",
            "category",
            "is_active",
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "config_key": "ai.base_url",
                "config_value": "http://localhost:11434/v1",
                "config_type": "string",
                "category": "ai",
                "description": "LLM API基础URL",
                "is_encrypted": False,
                "is_active": True,
            }
        }


class SystemConfigHistoryDoc(Document):
    """系统配置历史记录"""

    config_key: Indexed(str)  # 配置键
    old_value: Optional[str] = None  # 旧值
    new_value: Optional[str] = None  # 新值
    changed_by: Optional[str] = None  # 变更操作人
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    remark: Optional[str] = None  # 变更备注

    class Settings:
        name = "system_config_history"
        indexes = [
            "config_key",
            "changed_at",
        ]

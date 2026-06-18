"""
系统配置模型
"""
from typing import List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from beanie import Document
from pymongo import IndexModel, ASCENDING

from app.shared.core.document_mixins import TimestampedDocumentMixin


# ========== Beanie 文档模型 ==========

class SysWorkTypeDoc(Document, TimestampedDocumentMixin):
    """事项类型 - 数据库模型"""
    code: str = Field(..., description="类型编码（唯一）")
    name: str = Field(..., description="类型名称")

    class Settings:
        name = "sys_work_types"
        indexes = [
            IndexModel("code", unique=True)
        ]


class SysWorkflowStateDoc(Document, TimestampedDocumentMixin):
    """流程状态 - 数据库模型"""
    code: str = Field(..., description="状态编码（唯一）")
    name: str = Field(..., description="状态名称")
    is_end: bool = Field(default=False, description="是否为终点状态")

    class Settings:
        name = "sys_workflow_states"
        indexes = [
            IndexModel("code", unique=True)
        ]


class SysWorkflowConfigDoc(Document, TimestampedDocumentMixin):
    """流程配置 - 数据库模型"""
    type_code: str = Field(..., description="事项类型标识")
    from_state: str = Field(..., description="起始状态编码")
    action: str = Field(..., description="触发动作名称")
    to_state: str = Field(..., description="目标状态编码")
    target_owner_strategy: str = Field(default="KEEP", description="处理人策略")
    required_fields: List[str] = Field(default_factory=list, description="必填业务字段列表")
    properties: Dict[str, Any] = Field(default_factory=dict, description="扩展属性")

    class Settings:
        name = "sys_workflow_configs"
        indexes = [
            IndexModel(
                [("type_code", ASCENDING), ("from_state", ASCENDING), ("action", ASCENDING)],
                unique=True
            ),
            IndexModel("type_code")
        ]


# ========== Pydantic 响应模型 (API) ==========

class SysWorkTypeModel(BaseModel):
    code: str
    name: str


class SysWorkflowStateModel(BaseModel):
    code: str
    name: str
    is_end: bool


class SysWorkflowConfigModel(BaseModel):
    type_code: str
    from_state: str
    action: str
    to_state: str
    target_owner_strategy: str
    required_fields: List[str]
    properties: Dict[str, Any]

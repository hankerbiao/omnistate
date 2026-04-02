"""
需求与用例定义层 - 测试需求模型 (Beanie ODM 版本)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


# ========== Beanie 文档模型 ==========

class TestRequirementDoc(Document):
    """测试需求 - 数据库模型
    """
    __test__ = False
    req_id: str = Field(..., description="唯一业务编号（如 TR-2026-001）")
    workflow_item_id: Optional[str] = Field(None, description="关联工作流事项 ID")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = Field(None, description="详细技术规范与验证目标")
    technical_spec: Optional[str] = Field(None, description="技术规范")
    target_components: List[str] = Field(default_factory=list, description="BOM 覆盖范围")
    firmware_version: Optional[str] = Field(None, description="固件版本")
    priority: str = Field(default="P1", description="优先级")
    key_parameters: List[Dict[str, str]] = Field(default_factory=list, description="关键参数")
    risk_points: Optional[str] = Field(None, description="风险点")
    tpm_owner_id: str = Field(..., description="需求创建人/项目经理 ID")
    manual_dev_id: Optional[str] = Field(None, description="测试用例开发工程师 ID")
    auto_dev_id: Optional[str] = Field(None, description="自动化脚本开发工程师 ID")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表")
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_requirements"
        indexes = [
            IndexModel("req_id", unique=True),
            IndexModel("tpm_owner_id"),
            IndexModel("manual_dev_id"),
            IndexModel("auto_dev_id"),
            IndexModel("is_deleted"),
            IndexModel("created_at"),
            IndexModel([("tpm_owner_id", ASCENDING), ("created_at", DESCENDING)]),
        ]


# ========== Pydantic 响应模型 (API) ==========

class TestRequirementModel(BaseModel):
    id: Optional[str] = None
    req_id: str
    workflow_item_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    technical_spec: Optional[str] = None
    target_components: List[str]
    firmware_version: Optional[str] = None
    priority: str
    key_parameters: List[Dict[str, str]]
    risk_points: Optional[str] = None
    tpm_owner_id: str
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    status: str
    attachments: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

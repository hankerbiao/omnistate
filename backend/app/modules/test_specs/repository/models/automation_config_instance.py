"""自动化用例执行配置实例模型。"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import Document, Insert, Save, before_event
from pydantic import BaseModel, ConfigDict, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from app.modules.test_specs.repository.models.automation_test_case import ConfigFieldModel


class AutomationConfigInstanceDoc(Document):
    """自动化用例某次执行填写的配置实例。"""
    __test__ = False
    execution_id: str = Field(..., description="执行配置业务编号")
    auto_case_id: str = Field(..., description="自动化用例业务编号")
    version: str = Field(..., description="自动化用例版本")
    config_data: Dict[str, Any] = Field(default_factory=dict, description="执行配置 JSON")
    param_spec_snapshot: List[ConfigFieldModel] = Field(default_factory=list, description="参数规范快照")
    status: str = Field(default="SUBMITTED", description="状态（DRAFT/SUBMITTED/APPLIED）")
    created_by: Optional[str] = Field(None, description="创建者 user_id")
    updated_by: Optional[str] = Field(None, description="更新者 user_id")
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "automation_config_instances"
        indexes = [
            IndexModel([("execution_id", ASCENDING)], unique=True),
            IndexModel([("auto_case_id", ASCENDING), ("version", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel("status"),
            IndexModel("created_by"),
            IndexModel("is_deleted"),
        ]


class AutomationConfigInstanceModel(BaseModel):
    """自动化执行配置实例响应模型。"""
    id: Optional[str] = None
    execution_id: str
    auto_case_id: str
    version: str
    config_data: Dict[str, Any]
    param_spec_snapshot: List[ConfigFieldModel]
    status: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

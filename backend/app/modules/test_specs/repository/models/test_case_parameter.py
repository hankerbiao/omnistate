"""
测试用例执行参数模型
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from beanie import Document, before_event, Save, Insert
from pydantic import BaseModel, ConfigDict, Field
from pymongo import IndexModel, ASCENDING, DESCENDING


class TestCaseParameterDoc(Document):
    """测试用例参数配置表。"""
    __test__ = False

    case_id: str = Field(..., description="测试用例业务 ID")
    parameter_set_id: str = Field(..., description="参数集 ID")
    profile_name: Optional[str] = Field(None, description="参数集名称")
    framework: Optional[str] = Field(None, description="适用执行框架")
    env_scope: Optional[str] = Field(None, description="环境范围")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="执行参数")
    is_default: bool = Field(default=False, description="是否为默认参数集")
    version: int = Field(default=1, description="参数版本号")
    description: Optional[str] = Field(None, description="参数集说明")
    created_by: Optional[str] = Field(None, description="创建人")
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_case_parameters"
        indexes = [
            IndexModel([("case_id", ASCENDING), ("parameter_set_id", ASCENDING)], unique=True),
            IndexModel([("case_id", ASCENDING), ("is_default", ASCENDING)]),
            IndexModel("framework"),
            IndexModel("env_scope"),
            IndexModel("is_deleted"),
            IndexModel([("case_id", ASCENDING), ("updated_at", DESCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class TestCaseParameterModel(BaseModel):
    """测试用例参数 API 响应模型。"""
    __test__ = False

    id: Optional[str] = None
    case_id: str
    parameter_set_id: str
    profile_name: Optional[str] = None
    framework: Optional[str] = None
    env_scope: Optional[str] = None
    parameters: Dict[str, Any]
    is_default: bool
    version: int
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

"""
需求与用例定义层 - 自动化测试用例模型 (Beanie ODM 版本)
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


class AutomationTestCaseDoc(Document):
    """自动化测试用例库 - 数据库模型"""
    __test__ = False
    auto_case_id: str = Field(..., description="自动化用例唯一业务 ID（如 AUTO-CASE-10023）")
    name: str = Field(..., description="自动化用例名称")
    version: str = Field(default="1.0.0", description="自动化用例版本")
    status: str = Field(default="ACTIVE", description="状态（ACTIVE/DEPRECATED）")
    framework: Optional[str] = Field(None, description="自动化框架")
    automation_type: Optional[str] = Field(None, description="自动化类型")
    repo_url: Optional[str] = Field(None, description="脚本仓库地址")
    repo_branch: Optional[str] = Field(None, description="默认分支")
    script_entity_id: Optional[str] = Field(None, description="脚本实体 ID")
    entry_command: Optional[str] = Field(None, description="执行入口命令")
    runtime_env: Dict[str, Any] = Field(default_factory=dict, description="运行环境信息")
    tags: List[str] = Field(default_factory=list, description="标签")
    maintainer_id: Optional[str] = Field(None, description="维护人")
    reviewer_id: Optional[str] = Field(None, description="评审人")
    description: Optional[str] = Field(None, description="描述")
    assertions: List[str] = Field(default_factory=list, description="断言清单")
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "automation_test_cases"
        indexes = [
            IndexModel([("auto_case_id", ASCENDING), ("version", ASCENDING)], unique=True),
            IndexModel("status"),
            IndexModel("framework"),
            IndexModel("automation_type"),
            IndexModel("script_entity_id"),
            IndexModel("maintainer_id"),
            IndexModel("is_deleted"),
            IndexModel([("auto_case_id", ASCENDING), ("updated_at", DESCENDING)]),
            IndexModel("created_at"),
            IndexModel([("tags", ASCENDING), ("created_at", DESCENDING)]),
        ]


class AutomationTestCaseModel(BaseModel):
    """自动化测试用例 API 响应模型"""
    __test__ = False
    id: Optional[str] = None
    auto_case_id: str
    name: str
    version: str
    status: str
    framework: Optional[str] = None
    automation_type: Optional[str] = None
    repo_url: Optional[str] = None
    repo_branch: Optional[str] = None
    script_entity_id: Optional[str] = None
    entry_command: Optional[str] = None
    runtime_env: Dict[str, Any]
    tags: List[str]
    maintainer_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    description: Optional[str] = None
    assertions: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

"""自动化测试用例 API 模型"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class CreateAutomationTestCaseRequest(BaseModel):
    """创建自动化测试用例请求体"""
    auto_case_id: str = Field(..., description="自动化用例库 ID")
    name: str = Field(..., description="自动化用例名称")
    version: str = Field(default="1.0.0", description="自动化用例版本")
    status: str = Field(default="ACTIVE", description="状态")
    framework: Optional[str] = None
    automation_type: Optional[str] = None
    repo_url: Optional[str] = None
    repo_branch: Optional[str] = None
    script_entity_id: Optional[str] = None
    entry_command: Optional[str] = None
    runtime_env: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    maintainer_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    description: Optional[str] = None
    assertions: List[str] = Field(default_factory=list)


class UpdateAutomationTestCaseRequest(BaseModel):
    """更新自动化测试用例请求体"""
    name: Optional[str] = None
    status: Optional[str] = None
    framework: Optional[str] = None
    automation_type: Optional[str] = None
    repo_url: Optional[str] = None
    repo_branch: Optional[str] = None
    script_entity_id: Optional[str] = None
    entry_command: Optional[str] = None
    runtime_env: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    maintainer_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    description: Optional[str] = None
    assertions: Optional[List[str]] = None


class AutomationTestCaseResponse(BaseModel):
    """自动化测试用例响应体"""
    id: str
    auto_case_id: str
    name: str
    version: str
    status: str
    framework: Optional[str]
    automation_type: Optional[str]
    repo_url: Optional[str]
    repo_branch: Optional[str]
    script_entity_id: Optional[str]
    entry_command: Optional[str]
    runtime_env: Dict[str, Any]
    tags: List[str]
    maintainer_id: Optional[str]
    reviewer_id: Optional[str]
    description: Optional[str]
    assertions: List[str]
    created_at: datetime
    updated_at: datetime

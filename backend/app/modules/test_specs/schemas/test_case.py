"""测试用例 API 模型

约定说明：
- CreateRequest 仅定义前端可提交字段，不包含 status/created_at/updated_at。
- `tooling_req` 是顶层字段，不通过 `required_env` 做字段映射。
- Response 为后端完整返回结构（含 workflow/status/时间戳等服务端字段）。
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TestCaseStepSchema(BaseModel):
    __test__ = False
    step_id: str = Field(..., description="步骤 ID")
    name: str = Field(..., description="步骤名称")
    action: str = Field(..., description="执行动作")
    expected: str = Field(..., description="预期结果")


class AutomationCaseRefSchema(BaseModel):
    __test__ = False
    auto_case_id: str = Field(..., description="自动化用例库 ID")
    version: Optional[str] = Field(None, description="自动化用例版本")


class CreateTestCaseRequest(BaseModel):
    """创建用例请求体（字段需与前端创建 payload 一致）"""
    case_id: Optional[str] = Field(
        None,
        description="唯一业务编号（可选，前端不应提供，默认由后端生成）",
    )
    ref_req_id: str = Field(..., description="关联需求 req_id")
    title: str = Field(..., description="用例名称")
    version: int = 1
    is_active: bool = True
    change_log: Optional[str] = None
    owner_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_sec: Optional[int] = None
    target_components: List[str] = Field(default_factory=list)
    required_env: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    test_category: Optional[str] = None
    tooling_req: List[str] = Field(default_factory=list)
    is_destructive: bool = False
    pre_condition: Optional[str] = None
    post_condition: Optional[str] = None
    cleanup_steps: List[TestCaseStepSchema] = Field(default_factory=list)
    steps: List[TestCaseStepSchema] = Field(default_factory=list)
    is_need_auto: bool = False
    is_automated: bool = False
    automation_type: Optional[str] = None
    script_entity_id: Optional[str] = None
    automation_case_ref: Optional[AutomationCaseRefSchema] = None
    risk_level: Optional[str] = None
    failure_analysis: Optional[str] = None
    confidentiality: Optional[str] = None
    visibility_scope: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    deprecation_reason: Optional[str] = None
    approval_history: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateTestCaseRequest(BaseModel):
    """更新用例请求体（PATCH 语义，字段可按需提交）"""
    ref_req_id: Optional[str] = None
    title: Optional[str] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None
    change_log: Optional[str] = None
    owner_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_sec: Optional[int] = None
    target_components: Optional[List[str]] = None
    required_env: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    test_category: Optional[str] = None
    tooling_req: Optional[List[str]] = None
    is_destructive: Optional[bool] = None
    pre_condition: Optional[str] = None
    post_condition: Optional[str] = None
    cleanup_steps: Optional[List[TestCaseStepSchema]] = None
    steps: Optional[List[TestCaseStepSchema]] = None
    is_need_auto: Optional[bool] = None
    is_automated: Optional[bool] = None
    automation_type: Optional[str] = None
    script_entity_id: Optional[str] = None
    automation_case_ref: Optional[AutomationCaseRefSchema] = None
    risk_level: Optional[str] = None
    failure_analysis: Optional[str] = None
    confidentiality: Optional[str] = None
    visibility_scope: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    deprecation_reason: Optional[str] = None
    approval_history: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(extra="forbid")


class TestCaseResponse(BaseModel):
    """用例响应体（包含服务端生成字段）"""
    __test__ = False
    id: str
    case_id: str
    ref_req_id: str
    workflow_item_id: Optional[str] = None
    title: str
    version: int
    is_active: bool
    change_log: Optional[str]
    status: str
    owner_id: Optional[str]
    reviewer_id: Optional[str]
    auto_dev_id: Optional[str]
    priority: Optional[str]
    estimated_duration_sec: Optional[int]
    target_components: List[str]
    required_env: Dict[str, Any]
    tags: List[str]
    test_category: Optional[str]
    tooling_req: List[str]
    is_destructive: bool
    pre_condition: Optional[str]
    post_condition: Optional[str]
    cleanup_steps: List[TestCaseStepSchema]
    steps: List[TestCaseStepSchema]
    is_need_auto: bool
    is_automated: bool
    automation_type: Optional[str]
    script_entity_id: Optional[str]
    automation_case_ref: Optional[AutomationCaseRefSchema]
    risk_level: Optional[str]
    failure_analysis: Optional[str]
    confidentiality: Optional[str]
    visibility_scope: Optional[str]
    attachments: List[Dict[str, Any]]
    custom_fields: Dict[str, Any]
    deprecation_reason: Optional[str]
    approval_history: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class LinkAutomationCaseRequest(BaseModel):
    """测试用例关联自动化用例请求体"""
    auto_case_id: str = Field(..., description="自动化用例库 ID")
    version: Optional[str] = Field(None, description="自动化用例版本（为空时默认最新版本）")

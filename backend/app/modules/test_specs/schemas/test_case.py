"""测试用例 API 模型

## 关联关系说明

### 与 Requirement 模块的关联：
1. **ref_req_id** ↔ **Requirement.req_id**: 测试用例关联的需求业务编号（外键引用）
2. **target_components** ↔ **Requirement.target_components**: 目标组件列表应与关联需求保持一致或为其子集
3. **priority** ↔ **Requirement.priority**: 测试用例优先级，建议继承或不超过对应需求的优先级级别
4. **attachments** ↔ **Requirement.attachments**: 附件列表结构相同，测试用例可继承需求的附件或新增相关附件

### 业务规则：
- **多对一关系**: 多个测试用例可以关联同一个需求（ref_req_id 指向同一 req_id）
- **组件一致性**: 测试用例的 target_components 必须是需求 target_components 的子集
- **优先级规则**: 测试用例的 priority 不应超过对应需求的 priority 级别（如：需求为 P0，用例最高为 P1）
- **人员独立性**: 人员字段（owner_id, reviewer_id, auto_dev_id）在需求和用例层面不一定是同一个人，需要根据具体项目人员分配情况确定
- **工作流联动**: 需求的 workflow_item_id 与用例的 workflow_item_id 可建立关联关系
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
    ref_req_id: str = Field(..., description="关联需求 req_id（外键引用 Requirement.req_id）")
    title: str = Field(..., description="用例名称")
    version: int = Field(1, description="用例版本号，默认值为 1")
    is_active: bool = Field(True, description="用例是否激活状态")
    change_log: Optional[str] = Field(None, description="用例变更日志")
    owner_id: Optional[str] = Field(None, description="用例负责人 ID")
    reviewer_id: Optional[str] = Field(None, description="用例审核人 ID")
    auto_dev_id: Optional[str] = Field(None, description="自动化开发人员 ID")
    priority: Optional[str] = Field(None, description="用例优先级")
    estimated_duration_sec: Optional[int] = Field(None, description="预估执行时间（秒）")
    target_components: List[str] = Field(default_factory=list, description="目标组件列表")
    required_env: Dict[str, Any] = Field(default_factory=dict, description="所需测试环境配置")
    tags: List[str] = Field(default_factory=list, description="用例标签列表")
    test_category: Optional[str] = Field(None, description="测试分类")
    tooling_req: List[str] = Field(default_factory=list, description="测试工具需求列表")
    is_destructive: bool = Field(False, description="是否为破坏性测试")
    pre_condition: Optional[str] = Field(None, description="前置条件")
    post_condition: Optional[str] = Field(None, description="后置条件")
    cleanup_steps: List[TestCaseStepSchema] = Field(default_factory=list, description="清理步骤列表")
    steps: List[TestCaseStepSchema] = Field(default_factory=list, description="测试执行步骤列表")
    is_need_auto: bool = Field(False, description="是否需要自动化")
    is_automated: bool = Field(False, description="是否已实现自动化")
    automation_type: Optional[str] = Field(None, description="自动化类型")
    script_entity_id: Optional[str] = Field(None, description="脚本实体 ID")
    automation_case_ref: Optional[AutomationCaseRefSchema] = Field(None, description="自动化用例引用")
    risk_level: Optional[str] = Field(None, description="风险等级")
    failure_analysis: Optional[str] = Field(None, description="失败分析")
    confidentiality: Optional[str] = Field(None, description="保密等级")
    visibility_scope: Optional[str] = Field(None, description="可见范围")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="自定义字段")
    deprecation_reason: Optional[str] = Field(None, description="弃用原因")
    approval_history: List[Dict[str, Any]] = Field(default_factory=list, description="审批历史")


class UpdateTestCaseRequest(BaseModel):
    """更新用例请求体（PATCH 语义，字段可按需提交）"""
    ref_req_id: Optional[str] = Field(None, description="关联需求 req_id（外键引用 Requirement.req_id）")
    title: Optional[str] = Field(None, description="用例名称")
    version: Optional[int] = Field(None, description="用例版本号")
    is_active: Optional[bool] = Field(None, description="用例是否激活状态")
    change_log: Optional[str] = Field(None, description="用例变更日志")
    owner_id: Optional[str] = Field(None, description="用例负责人 ID")
    reviewer_id: Optional[str] = Field(None, description="用例审核人 ID")
    auto_dev_id: Optional[str] = Field(None, description="自动化开发人员 ID")
    priority: Optional[str] = Field(None, description="用例优先级")
    estimated_duration_sec: Optional[int] = Field(None, description="预估执行时间（秒）")
    target_components: Optional[List[str]] = Field(None, description="目标组件列表")
    required_env: Optional[Dict[str, Any]] = Field(None, description="所需测试环境配置")
    tags: Optional[List[str]] = Field(None, description="用例标签列表")
    test_category: Optional[str] = Field(None, description="测试分类")
    tooling_req: Optional[List[str]] = Field(None, description="测试工具需求列表")
    is_destructive: Optional[bool] = Field(None, description="是否为破坏性测试")
    pre_condition: Optional[str] = Field(None, description="前置条件")
    post_condition: Optional[str] = Field(None, description="后置条件")
    cleanup_steps: Optional[List[TestCaseStepSchema]] = Field(None, description="清理步骤列表")
    steps: Optional[List[TestCaseStepSchema]] = Field(None, description="测试执行步骤列表")
    is_need_auto: Optional[bool] = Field(None, description="是否需要自动化")
    is_automated: Optional[bool] = Field(None, description="是否已实现自动化")
    automation_type: Optional[str] = Field(None, description="自动化类型")
    script_entity_id: Optional[str] = Field(None, description="脚本实体 ID")
    automation_case_ref: Optional[AutomationCaseRefSchema] = Field(None, description="自动化用例引用")
    risk_level: Optional[str] = Field(None, description="风险等级")
    failure_analysis: Optional[str] = Field(None, description="失败分析")
    confidentiality: Optional[str] = Field(None, description="保密等级")
    visibility_scope: Optional[str] = Field(None, description="可见范围")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")
    deprecation_reason: Optional[str] = Field(None, description="弃用原因")
    approval_history: Optional[List[Dict[str, Any]]] = Field(None, description="审批历史")

    model_config = ConfigDict(extra="forbid")


class TestCaseResponse(BaseModel):
    """用例响应体（包含服务端生成字段）"""
    __test__ = False
    id: str = Field(..., description="用例唯一标识 ID")
    case_id: str = Field(..., description="用例业务编号")
    ref_req_id: str = Field(..., description="关联需求 req_id（外键引用 Requirement.req_id）")
    workflow_item_id: Optional[str] = Field(None, description="工作流项目 ID")
    title: str = Field(..., description="用例名称")
    version: int = Field(..., description="用例版本号")
    is_active: bool = Field(..., description="用例是否激活状态")
    change_log: Optional[str] = Field(None, description="用例变更日志")
    status: str = Field(..., description="用例状态")
    owner_id: Optional[str] = Field(None, description="用例负责人 ID")
    reviewer_id: Optional[str] = Field(None, description="用例审核人 ID")
    auto_dev_id: Optional[str] = Field(None, description="自动化开发人员 ID")
    priority: Optional[str] = Field(None, description="用例优先级")
    estimated_duration_sec: Optional[int] = Field(None, description="预估执行时间（秒）")
    target_components: List[str] = Field(..., description="目标组件列表")
    required_env: Dict[str, Any] = Field(..., description="所需测试环境配置")
    tags: List[str] = Field(..., description="用例标签列表")
    test_category: Optional[str] = Field(None, description="测试分类")
    tooling_req: List[str] = Field(..., description="测试工具需求列表")
    is_destructive: bool = Field(..., description="是否为破坏性测试")
    pre_condition: Optional[str] = Field(None, description="前置条件")
    post_condition: Optional[str] = Field(None, description="后置条件")
    cleanup_steps: List[TestCaseStepSchema] = Field(..., description="清理步骤列表")
    steps: List[TestCaseStepSchema] = Field(..., description="测试执行步骤列表")
    is_need_auto: bool = Field(..., description="是否需要自动化")
    is_automated: bool = Field(..., description="是否已实现自动化")
    automation_type: Optional[str] = Field(None, description="自动化类型")
    script_entity_id: Optional[str] = Field(None, description="脚本实体 ID")
    automation_case_ref: Optional[AutomationCaseRefSchema] = Field(None, description="自动化用例引用")
    risk_level: Optional[str] = Field(None, description="风险等级")
    failure_analysis: Optional[str] = Field(None, description="失败分析")
    confidentiality: Optional[str] = Field(None, description="保密等级")
    visibility_scope: Optional[str] = Field(None, description="可见范围")
    attachments: List[Dict[str, Any]] = Field(..., description="附件列表")
    custom_fields: Dict[str, Any] = Field(..., description="自定义字段")
    deprecation_reason: Optional[str] = Field(None, description="弃用原因")
    approval_history: List[Dict[str, Any]] = Field(..., description="审批历史")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class LinkAutomationCaseRequest(BaseModel):
    """测试用例关联自动化用例请求体"""
    auto_case_id: str = Field(..., description="自动化用例库 ID")
    version: Optional[str] = Field(None, description="自动化用例版本（为空时默认最新版本）")

"""测试需求 API 模型

## 关联关系说明

### 与 TestCase 模块的关联：
1. **req_id** ↔ **TestCase.ref_req_id**: 需求业务编号与测试用例关联需求的引用关系
2. **target_components** ↔ **TestCase.target_components**: 目标组件列表需保持一致，测试用例的目标组件应来源于需求
3. **priority** ↔ **TestCase.priority**: 优先级字段，建议测试用例优先级继承需求的优先级设置
4. **attachments** ↔ **TestCase.attachments**: 附件列表结构相同，需求和用例可共享附件

### 业务逻辑关联：
- 一个需求（req_id）可关联多个测试用例（多个 test_case.ref_req_id 指向同一个 req_id）
- 测试用例的 target_components 应是需求 target_components 的子集或完全一致
- 测试用例的 priority 建议不超过需求的优先级级别
- **注意**: 人员字段（auto_dev_id, manual_dev_id, tpm_owner_id）在需求和用例层面不一定是同一个人，需要根据具体项目人员分配情况来确定
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.modules.test_specs.repository.models.requirement import (
    REQUIREMENT_CATEGORY_CHOICES,
    REQUIREMENT_SOURCE_CHOICES,
)


class CreateRequirementRequest(BaseModel):
    """创建需求请求体（字段需与前端创建 payload 一致）
    """
    req_id: Optional[str] = Field(None, description="唯一业务编号（⚠️ 前端不应提供此字段，必须由后端生成）")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = Field(None, description="需求详细描述，包括业务场景和具体要求")
    category: Optional[str] = Field(None, description=f"需求分类：{'/'.join(REQUIREMENT_CATEGORY_CHOICES)}")
    tags: List[str] = Field(default_factory=list, description="自由标签")
    source: Optional[str] = Field(None, description=f"需求来源：{'/'.join(REQUIREMENT_SOURCE_CHOICES)}")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    baseline_version: Optional[str] = Field(None, description="基线版本（对比基准）")
    target_version: Optional[str] = Field(None, description="目标版本（待验证版本）")
    target_components: List[str] = Field(default_factory=list, description="目标组件列表，指定需求涉及的系统组件（测试用例的 target_components 应与此保持一致或为其子集）")
    firmware_version: Optional[str] = Field(None, description="目标固件版本号（兼容旧接口，新数据请用 baseline_version/target_version）")
    priority: str = Field("P1", description="需求优先级（P0/P1/P2/P3）（测试用例的 priority 建议继承此优先级设置）")
    key_parameters: List[Dict[str, str]] = Field(default_factory=list, description="关键参数列表，包含名称和值")
    risk_points: Optional[str] = Field(None, description="风险点和注意事项说明")
    tpm_owner_id: Optional[str] = Field(None, description="需求创建人/项目经理 ID（为空时默认当前登录用户）")
    manual_dev_id: Optional[str] = Field(None, description="手动测试开发人员 ID")
    auto_dev_id: Optional[str] = Field(None, description="自动化测试开发人员 ID")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表，包含文件名和文件内容等（测试用例可继承或新增相关附件）")
    planned_start_date: Optional[str] = Field(None, description="计划开始日期（YYYY-MM-DD）")
    planned_end_date: Optional[str] = Field(None, description="计划结束日期（YYYY-MM-DD）")


class UpdateRequirementRequest(BaseModel):
    """更新需求请求体（PATCH 语义，字段可按需提交）"""
    title: Optional[str] = Field(None, description="需求简述")
    description: Optional[str] = Field(None, description="需求详细描述，包括业务场景和具体要求")
    category: Optional[str] = Field(None, description="需求分类")
    tags: Optional[List[str]] = Field(None, description="自由标签")
    source: Optional[str] = Field(None, description="需求来源")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    baseline_version: Optional[str] = Field(None, description="基线版本")
    target_version: Optional[str] = Field(None, description="目标版本")
    target_components: Optional[List[str]] = Field(None, description="目标组件列表")
    firmware_version: Optional[str] = Field(None, description="目标固件版本号")
    priority: Optional[str] = Field(None, description="需求优先级（P0/P1/P2/P3）")
    key_parameters: Optional[List[Dict[str, str]]] = Field(None, description="关键参数列表")
    risk_points: Optional[str] = Field(None, description="风险点和注意事项说明")
    tpm_owner_id: Optional[str] = Field(None, description="需求创建人/项目经理 ID")
    manual_dev_id: Optional[str] = Field(None, description="手动测试开发人员 ID")
    auto_dev_id: Optional[str] = Field(None, description="自动化测试开发人员 ID")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")
    planned_start_date: Optional[str] = Field(None, description="计划开始日期（YYYY-MM-DD）")
    planned_end_date: Optional[str] = Field(None, description="计划结束日期（YYYY-MM-DD）")

    model_config = ConfigDict(extra="forbid")


class RequirementResponse(BaseModel):
    """需求响应体（包含服务端生成字段）"""
    id: str = Field(..., description="需求唯一标识 ID")
    req_id: str = Field(..., description="需求业务编号")
    workflow_item_id: Optional[str] = Field(None, description="工作流项目 ID")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = Field(None, description="需求详细描述")
    category: Optional[str] = Field(None, description="需求分类")
    tags: List[str] = Field(default_factory=list, description="自由标签")
    source: Optional[str] = Field(None, description="需求来源")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    baseline_version: Optional[str] = Field(None, description="基线版本")
    target_version: Optional[str] = Field(None, description="目标版本")
    target_components: List[str] = Field(default_factory=list, description="目标组件列表")
    firmware_version: Optional[str] = Field(None, description="固件版本（兼容旧数据）")
    priority: str = Field(default="P1", description="需求优先级")
    key_parameters: List[Dict[str, str]] = Field(default_factory=list, description="关键参数列表")
    risk_points: Optional[str] = Field(None, description="风险点和注意事项")
    tpm_owner_id: str = Field(default="", description="TPM负责人 ID")
    tpm_owner_name: Optional[str] = Field(None, description="TPM负责人姓名")
    manual_dev_id: Optional[str] = Field(None, description="手动测试开发人员 ID")
    manual_dev_name: Optional[str] = Field(None, description="手动测试开发人员姓名")
    auto_dev_id: Optional[str] = Field(None, description="自动化测试开发人员 ID")
    auto_dev_name: Optional[str] = Field(None, description="自动化测试开发人员姓名")
    case_count: int = Field(default=0, description="关联测试用例数量")
    status: str = Field(default="", description="需求状态")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表")
    planned_start_date: Optional[str] = Field(None, description="计划开始日期")
    planned_end_date: Optional[str] = Field(None, description="计划结束日期")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    # 工作流相关字段
    creator: Optional[str] = Field(None, description="工作流创建人 ID")
    creator_name: Optional[str] = Field(None, description="工作流创建人名称")
    current_owner: Optional[str] = Field(None, description="工作流当前负责人 ID")
    current_owner_name: Optional[str] = Field(None, description="工作流当前负责人名称")

"""
需求与用例定义层 - 测试用例模型 (Beanie ODM 版本)
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING

from app.shared.core.document_mixins import TimestampedDocumentMixin, SoftDeleteDocumentMixin, ProjectRelatedMixin


# ========== 子结构 ==========

class TestCaseStepEmbedded(BaseModel):
    """测试用例步骤（执行步骤 / 清理步骤）"""
    step_id: str = Field(..., description="步骤稳定标识")
    name: str = Field(..., description="步骤短标题")
    action: str = Field(..., description="执行动作")
    expected: str = Field(..., description="期望结果")


# ========== Beanie 文档模型 ==========

class TestCaseDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin, ProjectRelatedMixin):
    """测试用例 - 数据库模型
    """
    __test__ = False
    case_id: str = Field(..., description="唯一业务编号（如 TC-MEM-001）")
    lab_id: str = Field(..., description="所属 Lab（FK → TestLabDoc.lab_id）")
    catalog_path: List[str] = Field(..., description="目录路径段（≥1，小写存储）")
    catalog_path_key: str = Field(..., description="路径查询键，如 a/b/c")
    ref_req_id: Optional[str] = Field(None, description="关联需求 req_id（可选）")
    workflow_item_id: Optional[str] = Field(None, description="关联工作流事项 ID")
    title: str = Field(..., description="用例名称")
    version: int = Field(default=1, description="版本号")
    is_active: bool = Field(default=True, description="是否为当前有效版本")
    change_log: Optional[str] = Field(None, description="版本变更摘要")
    owner_id: Optional[str] = Field(None, description="用例责任人")
    reviewer_id: Optional[str] = Field(None, description="评审人")
    auto_dev_id: Optional[str] = Field(None, description="自动化开发责任人")
    priority: Optional[str] = Field(None, description="优先级")
    estimated_duration_sec: Optional[int] = Field(None, description="预估执行耗时(秒)")
    required_env: Dict[str, Any] = Field(default_factory=dict, description="环境要求")
    tags: List[str] = Field(default_factory=list, description="标签")
    test_category: Optional[str] = Field(None, description="测试分类")
    is_destructive: bool = Field(default=False, description="是否为破坏性测试")
    pre_condition: Optional[str] = Field(None, description="前置条件")
    post_condition: Optional[str] = Field(None, description="后置条件")
    risk_level: Optional[str] = Field(None, description="风险等级")
    failure_analysis: Optional[str] = Field(None, description="失败分析建议")
    confidentiality: Optional[str] = Field(None, description="机密等级")
    visibility_scope: Optional[str] = Field(None, description="可见范围")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="附件列表")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="自定义字段")
    deprecation_reason: Optional[str] = Field(None, description="废弃原因")
    approval_history: List[Dict[str, Any]] = Field(default_factory=list, description="审批记录")
    steps: List[TestCaseStepEmbedded] = Field(default_factory=list, description="执行步骤")
    cleanup_steps: List[TestCaseStepEmbedded] = Field(default_factory=list, description="清理步骤")
    linked_auto_case_id: Optional[str] = Field(default=None, description="关联的自动化用例 business id")
    embedding: Optional[list[float]] = Field(default=None, description="语义向量（用于语义搜索）")

    @field_validator("cleanup_steps", mode="before")
    @classmethod
    def normalize_cleanup_steps(cls, v: Any) -> Any:
        """兼容旧数据：清理步骤可能存为字符串数组而非结构体"""
        if not isinstance(v, list):
            return v
        normalized = []
        for i, item in enumerate(v):
            if isinstance(item, str):
                normalized.append(TestCaseStepEmbedded(
                    step_id=f"cs_{i}",
                    name=item,
                    action=item,
                    expected="环境恢复",
                ))
            else:
                normalized.append(item)
        return normalized

    class Settings:
        name = "test_cases"
        indexes = [
            *SoftDeleteDocumentMixin.Settings.indexes,
            *ProjectRelatedMixin.Settings.indexes,
            IndexModel("case_id", unique=True),
            IndexModel("lab_id"),
            IndexModel("catalog_path_key"),
            IndexModel("ref_req_id"),
            IndexModel("owner_id"),
            IndexModel("reviewer_id"),
            IndexModel("priority"),
            IndexModel("is_active"),
            IndexModel([("linked_auto_case_id", ASCENDING)], sparse=True),
            IndexModel([("ref_req_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel("created_at"),
        ]


# ========== Pydantic 响应模型 (API) ==========

class TestCaseModel(BaseModel):
    __test__ = False
    id: Optional[str] = None
    case_id: str
    lab_id: str
    catalog_path: List[str]
    catalog_path_key: str
    ref_req_id: Optional[str] = None
    title: str
    version: int
    is_active: bool
    change_log: Optional[str] = None
    status: str
    owner_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_sec: Optional[int] = None
    required_env: Dict[str, Any]
    tags: List[str]
    test_category: Optional[str] = None
    is_destructive: bool
    pre_condition: Optional[str] = None
    post_condition: Optional[str] = None
    risk_level: Optional[str] = None
    failure_analysis: Optional[str] = None
    confidentiality: Optional[str] = None
    visibility_scope: Optional[str] = None
    attachments: List[Dict[str, Any]]
    custom_fields: Dict[str, Any]
    deprecation_reason: Optional[str] = None
    approval_history: List[Dict[str, Any]]
    steps: List[TestCaseStepEmbedded] = Field(default_factory=list)
    cleanup_steps: List[TestCaseStepEmbedded] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

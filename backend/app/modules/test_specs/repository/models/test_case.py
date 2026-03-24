"""
需求与用例定义层 - 测试用例模型 (Beanie ODM 版本)
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


# ========== 子结构 ==========

# ========== Beanie 文档模型 ==========

class TestCaseDoc(Document):
    """测试用例 - 数据库模型

    注意：status字段是工作流状态的投影，只读。
    实际状态来源是关联的BusWorkItemDoc.current_state。
    状态转换通过工作流系统自动同步到此字段。
    """
    __test__ = False
    case_id: str = Field(..., description="唯一业务编号（如 TC-MEM-001）")
    ref_req_id: str = Field(..., description="关联需求 req_id")
    workflow_item_id: Optional[str] = Field(None, description="关联工作流事项 ID")
    title: str = Field(..., description="用例名称")
    version: int = Field(default=1, description="版本号")
    is_active: bool = Field(default=True, description="是否为当前有效版本")
    change_log: Optional[str] = Field(None, description="版本变更摘要")
    status: str = Field(default="draft", description="状态（工作流状态的投影，只读）")
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
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_cases"
        indexes = [
            IndexModel("case_id", unique=True),
            IndexModel("ref_req_id"),
            IndexModel("status"),
            IndexModel("owner_id"),
            IndexModel("reviewer_id"),
            IndexModel("priority"),
            IndexModel("is_active"),
            IndexModel("is_deleted"),
            IndexModel([("ref_req_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel("created_at"),
        ]


# ========== Pydantic 响应模型 (API) ==========

class TestCaseModel(BaseModel):
    __test__ = False
    id: Optional[str] = None
    case_id: str
    ref_req_id: str
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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

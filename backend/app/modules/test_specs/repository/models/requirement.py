"""
需求与用例定义层 - 测试需求模型 (Beanie ODM 版本)
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


# ========== 枚举常量 ==========

REQUIREMENT_CATEGORY_CHOICES = (
    "FUNCTIONAL", "PERFORMANCE", "STABILITY",
    "COMPATIBILITY", "SECURITY", "REGRESSION",
)
REQUIREMENT_SOURCE_CHOICES = (
    "CUSTOMER", "INTERNAL", "BUG", "SPEC", "REGULATION",
)


# ========== Beanie 文档模型 ==========

class TestRequirementDoc(Document):
    """测试需求 - 数据库模型
    """
    __test__ = False
    req_id: str = Field(..., description="唯一业务编号（如 TR-2026-001）")
    workflow_item_id: Optional[str] = Field(None, description="关联工作流事项 ID")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = Field(None, description="详细技术规范与验证目标")
    # ─── 新增字段 ──────────────────────────────────────────
    category: Optional[str] = Field(None, description="需求分类：FUNCTIONAL/PERFORMANCE/STABILITY/COMPATIBILITY/SECURITY/REGRESSION")
    tags: List[str] = Field(default_factory=list, description="自由标签")
    source: Optional[str] = Field(None, description="需求来源：CUSTOMER/INTERNAL/BUG/SPEC/REGULATION")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    baseline_version: Optional[str] = Field(None, description="基线版本（对比基准）")
    target_version: Optional[str] = Field(None, description="目标版本（待验证版本）")
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    case_count: int = Field(default=0, description="关联测试用例数量（冗余聚合）")
    tpm_owner_name: Optional[str] = Field(None, description="TPM负责人姓名（冗余）")
    manual_dev_name: Optional[str] = Field(None, description="手工用例开发姓名（冗余）")
    auto_dev_name: Optional[str] = Field(None, description="自动化开发姓名（冗余）")
    # ─── 既有字段 ──────────────────────────────────────────
    target_components: List[str] = Field(default_factory=list, description="BOM 覆盖范围")
    project_ids: List[str] = Field(default_factory=list, description="关联的项目 ID 列表")
    firmware_version: Optional[str] = Field(None, description="固件版本（兼容旧数据，新数据请用 baseline_version/target_version）")
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
            IndexModel("workflow_item_id"),
            IndexModel("category"),
            IndexModel("source"),
            IndexModel("tpm_owner_id"),
            IndexModel("manual_dev_id"),
            IndexModel("auto_dev_id"),
            IndexModel("is_deleted"),
            IndexModel("project_ids"),
            IndexModel("created_at"),
            IndexModel([("tpm_owner_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("workflow_item_id", ASCENDING), ("is_deleted", ASCENDING)]),
            IndexModel([("category", ASCENDING), ("priority", ASCENDING)]),
        ]


# ========== Pydantic 响应模型 (API) ==========

class TestRequirementModel(BaseModel):
    id: Optional[str] = None
    req_id: str
    workflow_item_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    source: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    baseline_version: Optional[str] = None
    target_version: Optional[str] = None
    firmware_version: Optional[str] = None
    planned_start_date: Optional[str] = None
    planned_end_date: Optional[str] = None
    case_count: int = 0
    target_components: List[str] = []
    priority: str = "P1"
    key_parameters: List[Dict[str, str]] = []
    risk_points: Optional[str] = None
    tpm_owner_id: str = ""
    tpm_owner_name: Optional[str] = None
    manual_dev_id: Optional[str] = None
    manual_dev_name: Optional[str] = None
    auto_dev_id: Optional[str] = None
    auto_dev_name: Optional[str] = None
    status: str = ""
    attachments: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

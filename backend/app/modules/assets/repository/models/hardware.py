"""
硬件与资产管理模型 (Beanie ODM 版本)

包含：
- MongoDB 持久化文档模型（Document）
- 对应的 Pydantic 响应模型（用于 API 层返回）
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


# ========== Beanie 文档模型 ==========

class ComponentLibraryDoc(Document):
    """部件字典 - 数据库模型"""
    part_number: str = Field(..., description="唯一物料编号（PN）")
    category: str = Field(..., description="大类")
    subcategory: Optional[str] = Field(None, description="子类")
    vendor: Optional[str] = Field(None, description="厂商")
    model: Optional[str] = Field(None, description="型号")
    revision: Optional[str] = Field(None, description="版本/步进")
    form_factor: Optional[str] = Field(None, description="物理规格")
    interface_type: Optional[str] = Field(None, description="接口类型")
    interface_gen: Optional[str] = Field(None, description="接口代际")
    protocol: Optional[str] = Field(None, description="协议/标准")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="通用规格字典")
    power_watt: Optional[float] = Field(None, description="典型功耗(W)")
    firmware_baseline: Optional[str] = Field(None, description="基线固件版本")
    spec: Dict[str, Any] = Field(default_factory=dict, description="详细规格扩展字段")
    datasheet_url: Optional[str] = Field(None, description="规格书/链接")
    lifecycle_status: Optional[str] = Field(None, description="生命周期状态")
    aliases: List[str] = Field(default_factory=list, description="兼容或别名")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "component_library"
        indexes = [
            IndexModel("part_number", unique=True),
            IndexModel("category"),
            IndexModel("subcategory"),
            IndexModel("vendor"),
            IndexModel("model"),
            IndexModel("lifecycle_status"),
            IndexModel([("category", ASCENDING), ("subcategory", ASCENDING)]),
            IndexModel([("vendor", ASCENDING), ("model", ASCENDING)]),
            IndexModel("created_at"),
        ]


class DutDoc(Document):
    """设备资产 - 数据库模型"""
    asset_id: str = Field(..., description="资产编号或 SN")
    model: str = Field(..., description="整机型号/平台")
    status: str = Field(default="可用", description="资产状态")
    owner_team: Optional[str] = Field(None, description="归属团队/项目")
    rack_location: Optional[str] = Field(None, description="机房/机柜/机位")
    bmc_ip: Optional[str] = Field(None, description="BMC IP")
    bmc_port: Optional[int] = Field(None, description="BMC 端口")
    os_ip: Optional[str] = Field(None, description="OS IP")
    os_port: Optional[int] = Field(None, description="OS 端口")
    login_username: Optional[str] = Field(None, description="登录用户名")
    login_password: Optional[str] = Field(None, description="登录密码")
    health_status: Optional[str] = Field(None, description="健康状态")
    notes: Optional[str] = Field(None, description="备注")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "dut_assets"
        indexes = [
            IndexModel("asset_id", unique=True),
            IndexModel("status"),
            IndexModel("owner_team"),
            IndexModel("rack_location"),
            IndexModel("bmc_ip"),
            IndexModel("os_ip"),
            IndexModel("health_status"),
            IndexModel([("owner_team", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("status", ASCENDING), ("health_status", ASCENDING)]),
            IndexModel("created_at"),
        ]


class TestPlanComponentDoc(Document):
    """测试计划关联部件 - 数据库模型"""
    plan_id: str = Field(..., description="关联的测试计划 ID")
    part_number: str = Field(..., description="关联的部件 PN")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "test_plan_components"
        indexes = [
            IndexModel([("plan_id", ASCENDING), ("part_number", ASCENDING)], unique=True),
            IndexModel("plan_id"),
            IndexModel("part_number"),
            IndexModel("created_at"),
        ]


# ========== Pydantic 响应模型 (API) ==========

class ComponentLibraryModel(BaseModel):
    id: Optional[str] = None
    part_number: str
    category: str
    subcategory: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    revision: Optional[str] = None
    form_factor: Optional[str] = None
    interface_type: Optional[str] = None
    interface_gen: Optional[str] = None
    protocol: Optional[str] = None
    attributes: Dict[str, Any]
    power_watt: Optional[float] = None
    firmware_baseline: Optional[str] = None
    spec: Dict[str, Any]
    datasheet_url: Optional[str] = None
    lifecycle_status: Optional[str] = None
    aliases: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DutModel(BaseModel):
    id: Optional[str] = None
    asset_id: str
    model: str
    status: str
    owner_team: Optional[str] = None
    rack_location: Optional[str] = None
    bmc_ip: Optional[str] = None
    bmc_port: Optional[int] = None
    os_ip: Optional[str] = None
    os_port: Optional[int] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    health_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestPlanComponentModel(BaseModel):
    id: Optional[str] = None
    plan_id: str
    part_number: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

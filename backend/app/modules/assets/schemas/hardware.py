"""硬件与资产管理 API 模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class CreateComponentRequest(BaseModel):
    part_number: str = Field(..., description="唯一物料编号（PN）")
    category: str = Field(..., description="大类")
    subcategory: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    revision: Optional[str] = None
    form_factor: Optional[str] = None
    interface_type: Optional[str] = None
    interface_gen: Optional[str] = None
    protocol: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    power_watt: Optional[float] = None
    firmware_baseline: Optional[str] = None
    spec: Dict[str, Any] = Field(default_factory=dict)
    datasheet_url: Optional[str] = None
    lifecycle_status: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)


class UpdateComponentRequest(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    revision: Optional[str] = None
    form_factor: Optional[str] = None
    interface_type: Optional[str] = None
    interface_gen: Optional[str] = None
    protocol: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    power_watt: Optional[float] = None
    firmware_baseline: Optional[str] = None
    spec: Optional[Dict[str, Any]] = None
    datasheet_url: Optional[str] = None
    lifecycle_status: Optional[str] = None
    aliases: Optional[List[str]] = None


class ComponentResponse(BaseModel):
    id: str
    part_number: str
    category: str
    subcategory: Optional[str]
    vendor: Optional[str]
    model: Optional[str]
    revision: Optional[str]
    form_factor: Optional[str]
    interface_type: Optional[str]
    interface_gen: Optional[str]
    protocol: Optional[str]
    attributes: Dict[str, Any]
    power_watt: Optional[float]
    firmware_baseline: Optional[str]
    spec: Dict[str, Any]
    datasheet_url: Optional[str]
    lifecycle_status: Optional[str]
    aliases: List[str]
    created_at: datetime
    updated_at: datetime


# ========== DUT ==========

class CreateDutRequest(BaseModel):
    asset_id: str = Field(..., description="资产编号或 SN")
    model: str = Field(..., description="整机型号/平台")
    status: str = Field(default="可用", description="设备状态")
    owner_team: Optional[str] = Field(None, description="归属团队")
    rack_location: Optional[str] = Field(None, description="机房/机柜/机位")
    bmc_ip: Optional[str] = Field(None, description="BMC IP")
    bmc_port: Optional[int] = Field(None, description="BMC 端口")
    os_ip: Optional[str] = Field(None, description="OS IP")
    os_port: Optional[int] = Field(None, description="OS 端口")
    login_username: Optional[str] = Field(None, description="登录用户名")
    login_password: Optional[str] = Field(None, description="登录密码")
    health_status: Optional[str] = Field(None, description="健康状态")
    notes: Optional[str] = Field(None, description="备注")


class UpdateDutRequest(BaseModel):
    model: Optional[str] = None
    status: Optional[str] = None
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


class DutResponse(BaseModel):
    id: str
    asset_id: str
    model: str
    status: str
    owner_team: Optional[str]
    rack_location: Optional[str]
    bmc_ip: Optional[str]
    bmc_port: Optional[int]
    os_ip: Optional[str]
    os_port: Optional[int]
    login_username: Optional[str]
    health_status: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

class CreateTestPlanComponentRequest(BaseModel):
    plan_id: str
    part_number: str


class TestPlanComponentResponse(BaseModel):
    id: str
    plan_id: str
    part_number: str
    created_at: datetime
    updated_at: datetime

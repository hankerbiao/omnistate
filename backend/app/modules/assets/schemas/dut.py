"""DUT 测试机 API 模型"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DutStatus(str, Enum):
    """DUT 状态枚举"""

    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class OsType(str, Enum):
    """操作系统类型"""

    LINUX = "Linux"
    WINDOWS = "Windows"
    OTHER = "Other"


class CreateDutRequest(BaseModel):
    """创建 DUT 请求体"""

    name: str = Field(..., description="机器名称", min_length=1, max_length=100)
    dut_id: Optional[str] = Field(None, description="DUT 业务编号（可选，不填则自动生成）")
    status: DutStatus = Field(default=DutStatus.AVAILABLE, description="状态")
    region: str = Field(default="default", description="区域")
    description: Optional[str] = Field(None, description="描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    bmc_ip: str = Field(..., description="BMC IP 地址")
    bmc_username: str = Field(default="admin", description="BMC 用户名")
    bmc_password: str = Field(..., description="BMC 密码")
    os_ip: str = Field(..., description="OS IP 地址")
    os_username: str = Field(default="root", description="OS 用户名")
    os_password: str = Field(..., description="OS 密码")
    os_type: OsType = Field(default=OsType.LINUX, description="操作系统类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义字段")


class UpdateDutRequest(BaseModel):
    """更新 DUT 请求体"""

    name: Optional[str] = Field(None, description="机器名称")
    status: Optional[DutStatus] = Field(None, description="状态")
    region: Optional[str] = Field(None, description="区域")
    description: Optional[str] = Field(None, description="描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    bmc_ip: Optional[str] = Field(None, description="BMC IP 地址")
    bmc_username: Optional[str] = Field(None, description="BMC 用户名")
    bmc_password: Optional[str] = Field(None, description="BMC 密码")
    os_ip: Optional[str] = Field(None, description="OS IP 地址")
    os_username: Optional[str] = Field(None, description="OS 用户名")
    os_password: Optional[str] = Field(None, description="OS 密码")
    os_type: Optional[OsType] = Field(None, description="操作系统类型")
    metadata: Optional[Dict[str, Any]] = Field(None, description="自定义字段")


class DutResponse(BaseModel):
    """DUT 响应体"""

    id: str = Field(..., description="文档 ID")
    dut_id: str = Field(..., description="DUT 业务编号")
    name: str = Field(..., description="机器名称")
    status: str = Field(..., description="状态")
    region: str = Field(..., description="区域")
    description: Optional[str] = Field(None, description="描述")
    tags: List[str] = Field(..., description="标签列表")
    bmc_ip: str = Field(..., description="BMC IP 地址")
    bmc_username: str = Field(..., description="BMC 用户名")
    os_ip: str = Field(..., description="OS IP 地址")
    os_username: str = Field(..., description="OS 用户名")
    os_type: str = Field(..., description="操作系统类型")
    metadata: Dict[str, Any] = Field(..., description="自定义字段")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = {"from_attributes": True}


class DutDetailResponse(DutResponse):
    """DUT 详情响应体（包含密码）"""

    bmc_password: str = Field(..., description="BMC 密码")
    os_password: str = Field(..., description="OS 密码")


class SyncTmmsRequest(BaseModel):
    """TMMS 同步请求体（预留）"""

    tmms_api_url: Optional[str] = Field(None, description="TMMS API 地址")
    force_sync: bool = Field(default=False, description="是否强制同步（覆盖本地修改）")


class SyncTmmsResponse(BaseModel):
    """TMMS 同步响应体（预留）"""

    success: bool = Field(..., description="同步是否成功")
    message: str = Field(..., description="同步结果信息")
    synced_count: int = Field(default=0, description="同步数量")
    error_count: int = Field(default=0, description="错误数量")
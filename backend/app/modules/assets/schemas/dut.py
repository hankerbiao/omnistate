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
    source: str = Field("manual", description="数据来源: manual/tmms/external")
    source_id: Optional[str] = Field(None, description="外部系统机器ID")
    last_synced_at: Optional[datetime] = Field(None, description="最后同步时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: Optional[str] = Field(None, description="创建人")

    model_config = {"from_attributes": True}


class DutDetailResponse(DutResponse):
    """DUT 详情响应体（包含密码）"""

    bmc_password: str = Field(..., description="BMC 密码")
    os_password: str = Field(..., description="OS 密码")


class SyncTmmsRequest(BaseModel):
    """TMMS 同步请求体"""

    regions: Optional[List[str]] = Field(None, description="限定同步区域（为空则全量同步）")
    conflict_strategy: str = Field(
        default="skip",
        description="冲突策略: skip=跳过已有记录, overwrite=覆盖本地, merge=合并（远程更新非敏感字段）",
    )
    prune_stale: bool = Field(default=False, description="是否将本地有但TMMS无的记录标记为RETIRED")


class SyncTmmsResponse(BaseModel):
    """TMMS 同步响应体"""

    success: bool = Field(..., description="同步是否成功")
    message: str = Field(..., description="同步结果信息")
    synced_count: int = Field(default=0, description="成功同步总数")
    created_count: int = Field(default=0, description="新建数量")
    updated_count: int = Field(default=0, description="更新数量")
    skipped_count: int = Field(default=0, description="跳过数量")
    error_count: int = Field(default=0, description="错误数量")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="逐条错误详情")


class ExternalMachineItem(BaseModel):
    """外部系统机器数据项"""

    external_id: str = Field(..., description="外部系统机器 ID")
    name: str = Field(..., description="机器名称")
    bmc_ip: str = Field(..., description="BMC IP 地址")
    os_ip: str = Field(..., description="OS IP 地址")
    region: str = Field(..., description="区域")
    os_type: str = Field(default="Linux", description="操作系统类型")
    status: str = Field(default="available", description="状态: available/in_use/maintenance/retired")
    owner: Optional[str] = Field(None, description="负责人/团队")
    model: Optional[str] = Field(None, description="机器型号")
    cpu: Optional[str] = Field(None, description="CPU 型号")
    memory: Optional[str] = Field(None, description="内存大小")
    storage: Optional[str] = Field(None, description="存储配置")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class ExternalMachinesResponse(BaseModel):
    """外部系统机器列表响应"""

    items: List[ExternalMachineItem] = Field(..., description="机器列表")
    total: int = Field(..., description="总数")
    regions: List[str] = Field(..., description="所有区域列表")


class ImportExternalMachineItem(BaseModel):
    """待导入的外部机器项（包含导入后的密码配置）"""

    external_id: str = Field(..., description="外部系统机器 ID")
    name: str = Field(..., description="机器名称")
    bmc_ip: str = Field(..., description="BMC IP 地址")
    bmc_password: str = Field(default="admin", description="BMC 密码")
    os_ip: str = Field(..., description="OS IP 地址")
    os_password: str = Field(default="root", description="OS 密码")
    region: str = Field(default="default", description="区域")
    os_type: OsType = Field(default=OsType.LINUX, description="操作系统类型")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ImportExternalMachinesRequest(BaseModel):
    """批量导入外部机器请求"""

    items: List[ImportExternalMachineItem] = Field(..., description="待导入的机器列表", min_length=1)


class ImportExternalMachinesResponse(BaseModel):
    """批量导入响应"""

    success: bool = Field(..., description="是否全部成功")
    message: str = Field(..., description="结果描述")
    total: int = Field(..., description="总数量")
    created_count: int = Field(default=0, description="成功创建数量")
    skipped_count: int = Field(default=0, description="跳过数量（已存在）")
    error_count: int = Field(default=0, description="错误数量")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="每条的导入结果")
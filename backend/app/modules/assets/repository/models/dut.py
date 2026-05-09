"""DUT 测试机文档模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel


class DutDoc(Document):
    """DUT 测试机文档"""

    # 业务编号
    dut_id: str = Field(..., description="DUT 业务编号")

    # 基本信息
    name: str = Field(..., description="机器名称")
    status: str = Field(default="AVAILABLE", description="状态: AVAILABLE/IN_USE/MAINTENANCE/RETIRED")
    region: str = Field(default="default", description="区域")
    description: Optional[str] = Field(None, description="描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")

    # BMC 信息（IPMI/Redfish）
    bmc_ip: str = Field(..., description="BMC IP 地址")
    bmc_username: str = Field(default="admin", description="BMC 用户名")
    bmc_password: str = Field(..., description="BMC 密码（明文）")

    # OS 信息
    os_ip: str = Field(..., description="操作系统 IP 地址")
    os_username: str = Field(default="root", description="OS 用户名")
    os_password: str = Field(..., description="OS 密码（明文）")
    os_type: str = Field(default="Linux", description="操作系统类型: Linux/Windows")

    # 扩展信息
    metadata: Dict[str, Any] = Field(default_factory=dict, description="自定义字段")

    # 审计字段
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新时间")

    class Settings:
        name = "duts"
        indexes = [
            IndexModel("dut_id", unique=True),
            IndexModel("name"),
            IndexModel("status"),
            IndexModel("region"),
            IndexModel("bmc_ip"),
            IndexModel("os_ip"),
        ]


class DutCreateModel(BaseModel):
    """DUT 创建数据模型（用于 service 层）"""

    dut_id: str
    name: str
    status: str = "AVAILABLE"
    region: str = "default"
    description: Optional[str] = None
    tags: List[str] = []
    bmc_ip: str
    bmc_username: str = "admin"
    bmc_password: str
    os_ip: str
    os_username: str = "root"
    os_password: str
    os_type: str = "Linux"
    metadata: Dict[str, Any] = {}
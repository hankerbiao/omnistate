"""
系统配置 Pydantic Schemas
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SystemConfigBase(BaseModel):
    """配置基础字段"""

    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="配置值")
    config_type: str = Field(default="string", description="值类型: string/integer/float/boolean/json")
    category: str = Field(default="general", description="分类: ai/system/general")
    description: Optional[str] = Field(None, description="配置描述")
    is_encrypted: bool = Field(default=False, description="是否加密")
    is_active: bool = Field(default=True, description="是否激活")


class SystemConfigCreate(SystemConfigBase):
    """创建配置请求"""

    pass


class SystemConfigUpdate(BaseModel):
    """更新配置请求"""

    config_value: str = Field(..., description="新配置值")
    remark: Optional[str] = Field(None, description="变更备注")


class BatchUpdateItem(BaseModel):
    """批量更新项"""

    config_key: str = Field(..., description="配置键")
    config_value: str = Field(..., description="新配置值")


class BatchUpdateRequest(BaseModel):
    """批量更新请求"""

    items: list[BatchUpdateItem] = Field(..., description="更新项列表")
    remark: Optional[str] = Field(None, description="变更备注")


class SystemConfigResponse(SystemConfigBase):
    """配置响应"""

    id: str = Field(..., description="文档ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    updated_by: Optional[str] = Field(None, description="更新人")

    class Config:
        from_attributes = True


class SystemConfigListResponse(BaseModel):
    """配置列表响应"""

    items: list[SystemConfigResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="总数")


class BatchUpdateResponse(BaseModel):
    """批量更新响应"""

    updated_count: int = Field(..., description="更新数量")


class TestConnectionRequest(BaseModel):
    """测试AI连接请求"""

    base_url: str = Field(..., description="API基础URL")
    model: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    timeout: int = Field(default=60, ge=5, le=300, description="超时时间(秒)")


class TestConnectionResponse(BaseModel):
    """测试AI连接响应"""

    success: bool = Field(..., description="是否成功")
    model: Optional[str] = Field(None, description="实际模型名")
    response_time_ms: Optional[int] = Field(None, description="响应时间(毫秒)")
    error: Optional[str] = Field(None, description="错误信息")


class ConfigHistoryResponse(BaseModel):
    """配置历史响应"""

    id: str = Field(..., description="记录ID")
    config_key: str = Field(..., description="配置键")
    old_value: Optional[str] = Field(None, description="旧值")
    new_value: Optional[str] = Field(None, description="新值")
    changed_by: Optional[str] = Field(None, description="变更人")
    changed_at: datetime = Field(..., description="变更时间")
    remark: Optional[str] = Field(None, description="备注")

    class Config:
        from_attributes = True


class AIConfig(BaseModel):
    """AI配置完整结构"""

    base_url: str
    model: str
    api_key: str = ""
    enabled: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60

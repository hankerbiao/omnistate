"""测试需求 API 模型

约定说明：
- CreateRequest 仅定义前端可提交字段，不包含 status/created_at/updated_at。
- UpdateRequest 使用全可选字段，配合 API 层 `exclude_unset=True` 做局部更新。
- Response 为后端完整返回结构（含服务端维护字段）。
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CreateRequirementRequest(BaseModel):
    """创建需求请求体（字段需与前端创建 payload 一致）"""
    req_id: str = Field(..., description="唯一业务编号")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = None
    technical_spec: Optional[str] = None
    target_components: List[str] = Field(default_factory=list)
    firmware_version: Optional[str] = None
    priority: str = "P1"
    key_parameters: List[Dict[str, str]] = Field(default_factory=list)
    risk_points: Optional[str] = None
    tpm_owner_id: Optional[str] = Field(None, description="需求创建人/项目经理 ID（为空时默认当前登录用户）")
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateRequirementRequest(BaseModel):
    """更新需求请求体（PATCH 语义，字段可按需提交）"""
    title: Optional[str] = None
    description: Optional[str] = None
    technical_spec: Optional[str] = None
    target_components: Optional[List[str]] = None
    firmware_version: Optional[str] = None
    priority: Optional[str] = None
    key_parameters: Optional[List[Dict[str, str]]] = None
    risk_points: Optional[str] = None
    tpm_owner_id: Optional[str] = None
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class RequirementResponse(BaseModel):
    """需求响应体（包含服务端生成字段）"""
    id: str
    req_id: str
    workflow_item_id: Optional[str] = None
    title: str
    description: Optional[str]
    technical_spec: Optional[str]
    target_components: List[str]
    firmware_version: Optional[str]
    priority: str
    key_parameters: List[Dict[str, str]]
    risk_points: Optional[str]
    tpm_owner_id: str
    manual_dev_id: Optional[str]
    auto_dev_id: Optional[str]
    status: str
    attachments: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

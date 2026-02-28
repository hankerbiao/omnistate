"""测试需求 API 模型"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CreateRequirementRequest(BaseModel):
    req_id: str = Field(..., description="唯一业务编号")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = None
    technical_spec: Optional[str] = None
    target_components: List[str] = Field(default_factory=list)
    firmware_version: Optional[str] = None
    priority: str = "P1"
    key_parameters: List[Dict[str, str]] = Field(default_factory=list)
    risk_points: Optional[str] = None
    tpm_owner_id: str = Field(..., description="需求创建人/项目经理 ID")
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    status: str = "待指派"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateRequirementRequest(BaseModel):
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
    status: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class RequirementResponse(BaseModel):
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

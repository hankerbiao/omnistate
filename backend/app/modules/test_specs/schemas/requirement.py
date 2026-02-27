"""测试需求 API 模型"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class CreateRequirementRequest(BaseModel):
    req_id: str = Field(..., description="唯一业务编号")
    title: str = Field(..., description="需求简述")
    description: Optional[str] = None
    target_components: List[str] = Field(default_factory=list)
    tpm_owner_id: str = Field(..., description="需求创建人/项目经理 ID")
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    status: str = Field(default="待指派")


class UpdateRequirementRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_components: Optional[List[str]] = None
    tpm_owner_id: Optional[str] = None
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None
    status: Optional[str] = None


class RequirementResponse(BaseModel):
    id: str
    req_id: str
    workflow_item_id: Optional[str] = None
    title: str
    description: Optional[str]
    target_components: List[str]
    tpm_owner_id: str
    manual_dev_id: Optional[str]
    auto_dev_id: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

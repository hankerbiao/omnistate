"""
工作流配置相关 Pydantic 模型

包含类型、状态、配置相关的请求/响应模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ==================== Response Models ====================

class WorkTypeResponse(BaseModel):
    """事项类型响应"""
    code: str
    name: str
    created_at: datetime
    updated_at: datetime


class WorkflowStateResponse(BaseModel):
    """流程状态响应"""
    code: str
    name: str
    is_end: bool
    created_at: datetime
    updated_at: datetime


class WorkflowConfigResponse(BaseModel):
    """流转配置响应"""
    id: int
    type_code: str
    from_state: str
    action: str
    to_state: str
    target_owner_strategy: str
    required_fields: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """通用成功响应"""
    message: str
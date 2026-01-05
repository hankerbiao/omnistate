"""
业务事项相关 Pydantic 模型

包含事项的 CRUD 和流转相关的请求/响应模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# ==================== Request Models ====================

class CreateWorkItemRequest(BaseModel):
    """创建业务事项请求"""
    type_code: str = Field(..., description="事项类型，如 REQUIREMENT, TEST_CASE")
    title: str = Field(..., min_length=1, max_length=200, description="事项标题")
    content: str = Field(..., description="事项内容")
    creator_id: int = Field(..., description="创建者用户ID")


class TransitionRequest(BaseModel):
    """状态流转请求"""
    action: str = Field(..., description="触发的动作，如 SUBMIT, APPROVE, REJECT, ASSIGN 等")
    operator_id: int = Field(..., description="执行操作的用户ID")
    form_data: Dict[str, Any] = Field(default_factory=dict, description="表单数据，如 target_owner_id, comment 等")


# ==================== Response Models ====================

class WorkItemResponse(BaseModel):
    """业务事项响应"""
    id: int
    type_code: str
    title: str
    content: str
    current_state: str
    current_owner_id: Optional[int]
    creator_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TransitionLogResponse(BaseModel):
    """流转日志响应"""
    id: int
    work_item_id: int
    from_state: str
    to_state: str
    action: str
    operator_id: int
    payload: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class TransitionResponse(BaseModel):
    """状态流转响应"""
    work_item_id: int
    from_state: str
    to_state: str
    action: str
    new_owner_id: Optional[int]
    work_item: WorkItemResponse
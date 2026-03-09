"""
业务事项相关 Pydantic 模型

包含事项的 CRUD 和流转相关的请求/响应模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from beanie import PydanticObjectId


# ==================== Request Models ====================

class CreateWorkItemRequest(BaseModel):
    """创建业务事项请求"""
    type_code: str = Field(..., description="事项类型，如 REQUIREMENT, TEST_CASE")
    title: str = Field(..., min_length=1, max_length=200, description="事项标题")
    content: str = Field(..., description="事项内容")
    parent_item_id: Optional[PydanticObjectId] = Field(
        default=None, description="父事项ID（例如测试用例所属的需求ID）"
    )

    model_config = ConfigDict(extra="forbid")


class TransitionRequest(BaseModel):
    """状态流转请求"""
    action: str = Field(..., description="触发的动作，如 SUBMIT, APPROVE, REJECT, ASSIGN 等")
    form_data: Dict[str, Any] = Field(default_factory=dict, description="表单数据，如 target_owner_id, comment 等")

    model_config = ConfigDict(extra="forbid")


# ==================== Response Models ====================

class WorkItemResponse(BaseModel):
    """业务事项响应"""
    item_id: str  # 修改字段名与前端保持一致
    type_code: str
    title: str
    content: str
    parent_item_id: Optional[str] = None
    current_state: str
    current_owner_id: Optional[str]
    creator_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransitionLogResponse(BaseModel):
    """流转日志响应"""
    id: str
    work_item_id: str
    from_state: str
    to_state: str
    action: str
    operator_id: str
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransitionResponse(BaseModel):
    """状态流转响应"""
    work_item_id: str
    from_state: str
    to_state: str
    action: str
    new_owner_id: Optional[str]
    work_item: WorkItemResponse

    model_config = ConfigDict(from_attributes=True)


class AvailableTransitionResponse(BaseModel):
    """可执行流转动作响应"""
    action: str
    to_state: str
    target_owner_strategy: str
    required_fields: List[str]


class AvailableTransitionsResponse(BaseModel):
    """可执行流转动作集合响应"""
    item_id: str
    current_state: str
    available_transitions: List[AvailableTransitionResponse]


class DeleteWorkItemData(BaseModel):
    """删除事项返回数据"""
    item_id: str

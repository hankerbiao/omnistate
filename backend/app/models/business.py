"""
业务实体模型 (Beanie ODM 版本)

该模块同时包含：
- MongoDB 持久化文档模型（Document）
- 对应的 Pydantic 响应模型（用于 API 层返回）
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from beanie import Document, Indexed, PydanticObjectId, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


# ========== Beanie 文档模型 ==========

class BusWorkItemDoc(Document):
    """业务事项 - 数据库模型（存储任务主体信息）"""
    type_code: str = Field(..., description="事项类型标识")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容/描述")
    current_state: str = Field(default="DRAFT", description="当前状态指针")
    current_owner_id: Optional[int] = Field(None, description="当前处理人")
    creator_id: int = Field(..., description="创建者用户ID")
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "bus_work_items"
        indexes = [
            IndexModel("type_code"),
            IndexModel("current_state"),
            IndexModel("current_owner_id"),
            IndexModel("creator_id"),
            IndexModel("is_deleted"),
            IndexModel("created_at"),
            # 复合索引优化：支持按 owner/creator 筛选并按时间倒序
            IndexModel([("current_owner_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("creator_id", ASCENDING), ("created_at", DESCENDING)])
        ]


class BusFlowLogDoc(Document):
    """流转日志 - 数据库模型（记录每一次状态变更轨迹）"""
    work_item_id: PydanticObjectId = Field(..., description="关联事项ID (ObjectId)")
    from_state: str = Field(..., description="变更前状态")
    to_state: str = Field(..., description="变更后状态")
    action: str = Field(..., description="触发动作")
    operator_id: int = Field(..., description="操作人ID")
    payload: Dict[str, Any] = Field(default_factory=dict, description="节点特有表单数据")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "bus_flow_logs"
        indexes = [
            IndexModel("work_item_id"),
            IndexModel([("work_item_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel("created_at")
        ]


# ========== Pydantic 响应模型 (API) ==========

class BusWorkItemModel(BaseModel):
    id: Optional[str] = None
    type_code: str
    title: str
    content: str
    current_state: str
    current_owner_id: Optional[int]
    creator_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusFlowLogModel(BaseModel):
    id: Optional[str] = None
    work_item_id: str
    from_state: str
    to_state: str
    action: str
    operator_id: int
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


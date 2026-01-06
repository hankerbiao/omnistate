from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import DateTime, func


class BusWorkItem(SQLModel, table=True):
    """
    业务事项实体（FlowInstance 快照）
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键，自增
    type_code: str  # 事项类型标识（与流程配置关联）
    title: str  # 标题
    content: str  # 内容/描述
    current_state: str = Field(default="DRAFT")  # 当前状态指针（状态机核心）
    current_owner_id: Optional[int] = None  # 当前处理人（可能为空）
    creator_id: int  # 创建者用户ID
    is_deleted: bool = Field(default=False, index=True)  # 逻辑删除标志

    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    )


class BusFlowLog(SQLModel, table=True):
    """
    流转审计日志（Transition 记录）
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键，自增
    work_item_id: int = Field(index=True)  # 关联事项ID（索引加速查询）
    from_state: str  # 变更前状态
    to_state: str  # 变更后状态
    action: str  # 触发动作
    operator_id: int  # 操作人ID
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # 节点特有表单数据

    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    )

from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import DateTime, func
from datetime import datetime


class SysWorkType(SQLModel, table=True):
    """
    事项类型定义表
    """
    code: str = Field(primary_key=True)  # 类型编码（主键）
    name: str  # 类型名称

    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    )


class SysWorkflowState(SQLModel, table=True):
    """
    流程状态定义表
    """
    code: str = Field(primary_key=True)  # 状态编码（主键）
    name: str  # 状态名称
    is_end: bool = Field(default=False)  # 是否为终点状态

    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    )


class OwnerStrategy(str, Enum):
    """
    目标处理人策略常量
    """
    KEEP = "KEEP"
    TO_CREATOR = "TO_CREATOR"
    TO_SPECIFIC_USER = "TO_SPECIFIC_USER"


class SysWorkflowConfig(SQLModel, table=True):
    """
    流程配置（Transition 地图）
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键，自增
    type_code: str = Field(index=True)  # 事项类型（索引）
    from_state: str  # 迁移起始状态
    action: str  # 触发动作
    to_state: str  # 迁移目标状态
    target_owner_strategy: str = Field(default=OwnerStrategy.KEEP)  # 处理人策略
    required_fields: List[str] = Field(default=[], sa_column=Column(JSON))  # 必填字段列表

    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    )

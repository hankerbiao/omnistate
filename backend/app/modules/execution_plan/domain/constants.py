"""
执行计划模块常量定义。

集中管理状态枚举值，避免字符串散落在各处。
"""
from __future__ import annotations

from enum import Enum


class PlanItemStatus(str, Enum):
    """计划条目执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAIL = "fail"


class PlanStatus(str, Enum):
    """执行计划状态。"""
    DRAFT = "draft"
    ACTIVE = "active"
    DONE = "done"
    ARCHIVED = "archived"


class ResultSource(str, Enum):
    """计划条目结果来源。"""
    MANUAL = "manual"
    AUTO = "auto"


# 手动回填结果时的状态映射
RESULT_TO_ITEM_STATUS: dict[bool, PlanItemStatus] = {
    True: PlanItemStatus.DONE,
    False: PlanItemStatus.FAIL,
}

"""
模型模块

导出：
- Pydantic 模型（用于 API 验证）
- MongoDB 文档模型（用于数据持久化）
"""
from typing import List, Dict, Any

# 枚举
from .enums import OwnerStrategy, WorkItemState
from .system import (
    SysWorkTypeModel,
    SysWorkflowStateModel,
    SysWorkflowConfigModel,
    # MongoDB 文档模型
    SysWorkTypeDoc,
    SysWorkflowStateDoc,
    SysWorkflowConfigDoc,
)

# 业务实体模型
from .business import (
    BusWorkItemModel,
    BusFlowLogModel,
    # MongoDB 文档模型
    BusWorkItemDoc,
    BusFlowLogDoc,
)

__all__ = [
    # 枚举
    "OwnerStrategy",
    "WorkItemState",
    # Pydantic 模型
    "SysWorkTypeModel",
    "SysWorkflowStateModel",
    "SysWorkflowConfigModel",
    "BusWorkItemModel",
    "BusFlowLogModel",
    # MongoDB 文档模型
    "SysWorkTypeDoc",
    "SysWorkflowStateDoc",
    "SysWorkflowConfigDoc",
    "BusWorkItemDoc",
    "BusFlowLogDoc",
]

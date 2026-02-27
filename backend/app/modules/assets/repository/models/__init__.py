"""
硬件与资产管理模型模块

导出：
- Pydantic 模型（用于 API 验证）
- MongoDB 文档模型（用于数据持久化）
"""
from .hardware import (
    ComponentLibraryModel,
    DutModel,
    TestPlanComponentModel,
    ComponentLibraryDoc,
    DutDoc,
    TestPlanComponentDoc,
)

__all__ = [
    "ComponentLibraryModel",
    "DutModel",
    "TestPlanComponentModel",
    "ComponentLibraryDoc",
    "DutDoc",
    "TestPlanComponentDoc",
]

"""硬件与资产管理 API 模型汇总"""
from .hardware import (
    CreateComponentRequest,
    UpdateComponentRequest,
    ComponentResponse,
    CreateDutRequest,
    UpdateDutRequest,
    DutResponse,
    CreateTestPlanComponentRequest,
    TestPlanComponentResponse,
)

__all__ = [
    "CreateComponentRequest",
    "UpdateComponentRequest",
    "ComponentResponse",
    "CreateDutRequest",
    "UpdateDutRequest",
    "DutResponse",
    "CreateTestPlanComponentRequest",
    "TestPlanComponentResponse",
]

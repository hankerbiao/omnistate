"""定义层 API 模型汇总"""
from .requirement import (
    CreateRequirementRequest,
    UpdateRequirementRequest,
    RequirementResponse,
)
from .test_case import (
    CreateTestCaseRequest,
    UpdateTestCaseRequest,
    TestCaseResponse,
    LinkAutomationCaseRequest,
)


__all__ = [
    "CreateRequirementRequest",
    "UpdateRequirementRequest",
    "RequirementResponse",
    "CreateTestCaseRequest",
    "UpdateTestCaseRequest",
    "TestCaseResponse",
    "LinkAutomationCaseRequest",
]

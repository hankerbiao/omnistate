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
from .automation_test_case import (
    CreateAutomationTestCaseRequest,
    UpdateAutomationTestCaseRequest,
    AutomationTestCaseResponse,
)

__all__ = [
    "CreateRequirementRequest",
    "UpdateRequirementRequest",
    "RequirementResponse",
    "CreateTestCaseRequest",
    "UpdateTestCaseRequest",
    "TestCaseResponse",
    "LinkAutomationCaseRequest",
    "CreateAutomationTestCaseRequest",
    "UpdateAutomationTestCaseRequest",
    "AutomationTestCaseResponse",
]

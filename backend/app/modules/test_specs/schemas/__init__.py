"""定义层 API 模型汇总"""
from .requirement import (
    CreateRequirementRequest,
    UpdateRequirementRequest,
    RequirementResponse,
)
from .test_case import (
    AutomationTestCaseReportResponse,
    AutomationTestCaseResponse,
    CreateTestCaseRequest,
    CreateAutomationTestCaseRequest,
    ReportAutomationCaseMetadataRequest,
    UpdateTestCaseRequest,
    TestCaseResponse,
    LinkAutomationCaseRequest,
)


__all__ = [
    "CreateRequirementRequest",
    "UpdateRequirementRequest",
    "RequirementResponse",
    "AutomationTestCaseReportResponse",
    "AutomationTestCaseResponse",
    "CreateAutomationTestCaseRequest",
    "ReportAutomationCaseMetadataRequest",
    "CreateTestCaseRequest",
    "UpdateTestCaseRequest",
    "TestCaseResponse",
    "LinkAutomationCaseRequest",
]

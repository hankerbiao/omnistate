"""定义层模型模块"""
from .requirement import TestRequirementDoc, TestRequirementModel
from .test_case import TestCaseDoc, TestCaseModel, AutomationCaseRef
from .automation_test_case import AutomationTestCaseDoc, AutomationTestCaseModel

__all__ = [
    "TestRequirementDoc",
    "TestRequirementModel",
    "TestCaseDoc",
    "TestCaseModel",
    "AutomationCaseRef",
    "AutomationTestCaseDoc",
    "AutomationTestCaseModel",
]

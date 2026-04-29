"""定义层模型模块"""
from .requirement import TestRequirementDoc, TestRequirementModel
from .test_case import TestCaseDoc, TestCaseModel
from .automation_test_case import (
    AutomationTestCaseDoc,
    AutomationTestCaseModel,
    CodeSnapshotModel,
    ConfigFieldModel,
    ReportMetaModel,
    ScriptRefModel,
)

__all__ = [
    "TestRequirementDoc",
    "TestRequirementModel",
    "TestCaseDoc",
    "TestCaseModel",
    "AutomationTestCaseDoc",
    "AutomationTestCaseModel",
    "ScriptRefModel",
    "CodeSnapshotModel",
    "ReportMetaModel",
    "ConfigFieldModel",
    "DOCUMENT_MODELS",
]

DOCUMENT_MODELS = [
    TestRequirementDoc,
    TestCaseDoc,
    AutomationTestCaseDoc,
]

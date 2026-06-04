"""定义层模型模块"""
from .requirement import TestRequirementDoc, TestRequirementModel
from .test_case import TestCaseDoc, TestCaseModel
from .test_lab import TestLabDoc
from .test_catalog_segment import TestCatalogSegmentDoc
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
    "TestLabDoc",
    "TestCatalogSegmentDoc",
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
    TestLabDoc,
    TestCatalogSegmentDoc,
    AutomationTestCaseDoc,
]

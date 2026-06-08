"""定义层模型模块"""
from .requirement import TestRequirementDoc, TestRequirementModel
from .test_case import TestCaseDoc, TestCaseModel
from .test_lab import TestLabDoc
from .test_catalog_segment import TestCatalogSegmentDoc
from .test_case_change_log import TestCaseChangeLogDoc
from .test_case_comment import TestCaseCommentDoc
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
    "TestCaseChangeLogDoc",
    "TestCaseCommentDoc",
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
    TestCaseChangeLogDoc,
    TestCaseCommentDoc,
    AutomationTestCaseDoc,
]

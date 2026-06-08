"""定义层服务模块"""
from .automation_test_case_service import AutomationTestCaseService
from .catalog_service import CatalogService
from .change_log_service import TestCaseChangeLogService
from .comment_service import TestCaseCommentService
from .lab_service import LabService
from .requirement_service import RequirementService
from .test_case_service import TestCaseService

__all__ = [
    "AutomationTestCaseService",
    "CatalogService",
    "LabService",
    "RequirementService",
    "TestCaseChangeLogService",
    "TestCaseCommentService",
    "TestCaseService",
]

from .commands import (
    # Phase 4: 显式命令对象
    AssignRequirementOwnersCommand,
    AssignTestCaseOwnersCommand,
    MoveTestCaseToRequirementCommand,
    LinkAutomationCaseCommand,
    UnlinkAutomationCaseCommand,
    UpdateRequirementContentCommand,
    UpdateTestCaseContentCommand,
    # 向后兼容的传统命令
    CreateRequirementCommand,
    UpdateRequirementCommand,
    DeleteRequirementCommand,
    CreateTestCaseCommand,
    UpdateTestCaseCommand,
    DeleteTestCaseCommand,
)
from .requirement_command_service import RequirementCommandService
from .test_case_command_service import TestCaseCommandService

__all__ = [
    # Phase 4: 显式命令对象
    "AssignRequirementOwnersCommand",
    "AssignTestCaseOwnersCommand",
    "MoveTestCaseToRequirementCommand",
    "LinkAutomationCaseCommand",
    "UnlinkAutomationCaseCommand",
    "UpdateRequirementContentCommand",
    "UpdateTestCaseContentCommand",
    # 向后兼容的传统命令
    "CreateRequirementCommand",
    "UpdateRequirementCommand",
    "DeleteRequirementCommand",
    "CreateTestCaseCommand",
    "UpdateTestCaseCommand",
    "DeleteTestCaseCommand",
    # 现有的应用服务
    "RequirementCommandService",
    "TestCaseCommandService",
]

"""测试规范应用层命令对象。"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AssignRequirementOwnersCommand:
    """分配需求负责人命令"""
    req_id: str
    tpm_owner_id: Optional[str] = None
    manual_dev_id: Optional[str] = None
    auto_dev_id: Optional[str] = None

    def validate(self) -> None:
        """验证命令参数"""
        if not any([self.tpm_owner_id, self.manual_dev_id, self.auto_dev_id]):
            raise ValueError("at least one owner must be specified")


@dataclass
class AssignTestCaseOwnersCommand:
    """分配测试用例负责人命令"""
    case_id: str
    owner_id: Optional[str] = None
    reviewer_id: Optional[str] = None
    auto_dev_id: Optional[str] = None

    def validate(self) -> None:
        """验证命令参数"""
        if not any([self.owner_id, self.reviewer_id, self.auto_dev_id]):
            raise ValueError("at least one owner must be specified")


@dataclass
class MoveTestCaseToRequirementCommand:
    """将测试用例移动到不同需求命令"""
    case_id: str
    target_req_id: str

    def validate(self) -> None:
        """验证命令参数"""
        if not str(self.case_id).strip():
            raise ValueError("case_id is required")
        if not str(self.target_req_id).strip():
            raise ValueError("target_req_id is required")


@dataclass
class LinkAutomationCaseCommand:
    """关联自动化测试用例命令"""
    case_id: str
    auto_case_id: str
    version: Optional[str] = None


@dataclass
class CreateRequirementCommand:
    """创建需求命令。"""
    payload: Dict[str, Any]


@dataclass
class UpdateRequirementCommand:
    """更新需求命令。"""
    req_id: str
    payload: Dict[str, Any]


@dataclass
class DeleteRequirementCommand:
    """删除需求命令。"""
    req_id: str


@dataclass
class CreateTestCaseCommand:
    """创建测试用例命令。"""
    payload: Dict[str, Any]


@dataclass
class UpdateTestCaseCommand:
    """更新测试用例命令。"""
    case_id: str
    payload: Dict[str, Any]


@dataclass
class DeleteTestCaseCommand:
    """删除测试用例命令。"""
    case_id: str

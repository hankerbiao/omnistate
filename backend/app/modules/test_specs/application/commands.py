"""测试规范领域命令对象 - Phase 4

这个模块定义了测试规范相关的显式命令，用于替代通用CRUD更新中的高风险操作。
根据Phase 4的要求，高风险操作必须通过显式命令进行，不能通过通用更新载荷。

高风险操作包括：
- 负责人分配/修改
- 测试用例在不同需求间的移动
- 工作流关联的修改
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List


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
        if self.case_id == self.target_req_id:
            raise ValueError("case_id and target_req_id cannot be the same")


@dataclass
class LinkAutomationCaseCommand:
    """关联自动化测试用例命令"""
    case_id: str
    auto_case_id: str
    version: Optional[str] = None


@dataclass
class UnlinkAutomationCaseCommand:
    """解除自动化测试用例关联命令"""
    case_id: str


@dataclass
class UpdateTestCaseContentCommand:
    """更新测试用例内容命令（安全的低风险内容更新）"""
    case_id: str
    content_updates: Dict[str, Any]

    def validate(self) -> None:
        """验证内容更新字段"""
        # 只允许更新内容字段，不允许更新关系或工作流相关字段
        forbidden_fields = {
            'ref_req_id', 'workflow_item_id', 'case_id', 'status',
            'owner_id', 'reviewer_id', 'auto_dev_id', 'is_deleted'
        }
        conflicts = set(self.content_updates.keys()) & forbidden_fields
        if conflicts:
            raise ValueError(
                f"cannot update relationship or workflow fields: {conflicts}. "
                "Use explicit commands instead."
            )


@dataclass
class UpdateRequirementContentCommand:
    """更新需求内容命令（安全的低风险内容更新）"""
    req_id: str
    content_updates: Dict[str, Any]

    def validate(self) -> None:
        """验证内容更新字段"""
        # 只允许更新内容字段，不允许更新关系或工作流相关字段
        forbidden_fields = {
            'req_id', 'workflow_item_id', 'status',
            'tpm_owner_id', 'manual_dev_id', 'auto_dev_id', 'is_deleted'
        }
        conflicts = set(self.content_updates.keys()) & forbidden_fields
        if conflicts:
            raise ValueError(
                f"cannot update relationship or workflow fields: {conflicts}. "
                "Use explicit commands instead."
            )


# Phase 4: 保持向后兼容性的传统命令（简单包装器）
@dataclass
class CreateRequirementCommand:
    """创建需求命令（向后兼容）"""
    payload: Dict[str, Any]


@dataclass
class UpdateRequirementCommand:
    """更新需求命令（向后兼容）"""
    req_id: str
    payload: Dict[str, Any]


@dataclass
class DeleteRequirementCommand:
    """删除需求命令（向后兼容）"""
    req_id: str


@dataclass
class CreateTestCaseCommand:
    """创建测试用例命令（向后兼容）"""
    payload: Dict[str, Any]


@dataclass
class UpdateTestCaseCommand:
    """更新测试用例命令（向后兼容）"""
    case_id: str
    payload: Dict[str, Any]


@dataclass
class DeleteTestCaseCommand:
    """删除测试用例命令（向后兼容）"""
    case_id: str
from copy import deepcopy

from app.modules.test_specs.application._workflow_command_support import (
    delete_entity_or_work_item,
    ensure_entity,
    ensure_permission,
)
from app.modules.test_specs.application.commands import (
    AssignTestCaseOwnersCommand,
    LinkAutomationCaseCommand,
    MoveTestCaseToRequirementCommand,
    CreateTestCaseCommand,
    UpdateTestCaseCommand,
    DeleteTestCaseCommand,
)
from app.modules.test_specs.domain.exceptions import RequirementNotFoundError, TestCaseNotFoundError
from app.modules.test_specs.domain.policies import can_delete_test_case, can_update_test_case
from app.modules.test_specs.service import TestCaseService, RequirementService
from app.modules.workflow.application import OperationContext, WorkflowCommandService


class TestCaseCommandService:
    """
    测试用例命令服务类，负责处理测试用例的各种命令操作。

    该服务类封装了测试用例的创建、更新、删除以及与自动化测试用例的关联操作，
    并与工作流服务集成，确保操作符合权限策略和业务规则。
    """
    __test__ = False

    def __init__(
        self,
        test_case_service: TestCaseService,
        requirement_service: RequirementService,
        workflow_command_service: WorkflowCommandService,
    ):
        """
        初始化测试用例命令服务。

        Args:
            test_case_service: 测试用例服务实例，用于执行测试用例相关的数据库操作
            requirement_service: 需求服务实例，用于验证目标需求
            workflow_command_service: 工作流命令服务实例，用于处理工作流相关的操作
        """
        self._test_case_service = test_case_service
        self._requirement_service = requirement_service
        self._workflow_command_service = workflow_command_service

    async def create_test_case(
        self,
        context: OperationContext,
        command: CreateTestCaseCommand,
    ) -> dict:
        """
        创建新的测试用例。

        如果请求中没有指定owner_id，则默认将当前操作者设置为负责人。
        这确保每个测试用例都有一个明确的负责人。

        Args:
            context: 操作上下文，包含执行操作的用户信息
            command: 创建测试用例命令，包含测试用例的基本信息

        Returns:
            创建成功的测试用例数据字典

        Raises:
            相关异常可能由底层服务抛出
        """
        payload = deepcopy(command.payload)
        owner_id = str(payload.get("owner_id") or "").strip()
        if not owner_id:
            payload["owner_id"] = context.actor_id
        return await self._test_case_service.create_test_case(payload)

    async def update_test_case(
        self,
        context: OperationContext,
        command: UpdateTestCaseCommand,
    ) -> dict:
        """
        更新现有测试用例。

        执行以下步骤：
        1. 验证更新字段不为空
        2. 获取测试用例信息并验证存在性
        3. 获取关联的工作流项（如果有）
        4. 检查更新权限
        5. 执行更新操作

        Args:
            context: 操作上下文，包含执行操作的用户信息
            command: 更新测试用例命令，包含测试用例ID和更新字段

        Returns:
            更新后的测试用例数据字典

        Raises:
            ValueError: 更新字段为空时抛出
            TestCaseNotFoundError: 测试用例不存在时抛出
            PermissionDeniedError: 没有更新权限时抛出
        """
        if not command.payload:
            raise ValueError("no fields to update")

        test_case = await ensure_entity(
            command.case_id,
            self._test_case_service.get_test_case,
            TestCaseNotFoundError,
        )
        await ensure_permission(
            context,
            test_case,
            can_update_test_case,
            "update test case",
            self._workflow_command_service.get_work_item_by_id,
        )

        return await self._test_case_service.update_test_case(command.case_id, command.payload)

    async def delete_test_case(
        self,
        context: OperationContext,
        command: DeleteTestCaseCommand,
    ) -> None:
        """
        删除测试用例。

        执行以下步骤：
        1. 获取测试用例信息并验证存在性
        2. 获取关联的工作流项（如果有）
        3. 检查删除权限
        4. 如果有关联工作流项，先删除工作流项
        5. 否则直接删除测试用例

        Args:
            context: 操作上下文，包含执行操作的用户信息
            command: 删除测试用例命令，包含要删除的测试用例ID

        Raises:
            TestCaseNotFoundError: 测试用例不存在时抛出
            PermissionDeniedError: 没有删除权限时抛出
        """
        test_case = await ensure_entity(
            command.case_id,
            self._test_case_service.get_test_case,
            TestCaseNotFoundError,
        )
        workflow_item_id = await ensure_permission(
            context,
            test_case,
            can_delete_test_case,
            "delete test case",
            self._workflow_command_service.get_work_item_by_id,
        )
        await delete_entity_or_work_item(
            context,
            self._workflow_command_service,
            workflow_item_id,
            lambda: self._test_case_service.delete_test_case(command.case_id),
        )

    async def link_automation_case(
        self,
        context: OperationContext,
        command: LinkAutomationCaseCommand,
    ) -> dict:
        """
        将测试用例与自动化测试用例进行关联。

        此操作用于建立测试用例与自动化测试用例之间的关联关系，
        支持版本控制。操作不需要权限检查，所有用户都可以执行。

        Args:
            context: 操作上下文（此方法中未使用）
            command: 关联命令，包含测试用例ID、自动化测试用例ID和版本信息

        Returns:
            关联操作的结果数据字典

        Raises:
            相关异常可能由底层服务抛出
        """
        test_case = await ensure_entity(
            command.case_id,
            self._test_case_service.get_test_case,
            TestCaseNotFoundError,
        )
        await ensure_permission(
            context,
            test_case,
            can_update_test_case,
            "link automation case",
            self._workflow_command_service.get_work_item_by_id,
        )

        return await self._test_case_service.link_automation_case(
            case_id=command.case_id,
            auto_case_id=command.auto_case_id,
            version=command.version,
        )

    async def assign_owners(
        self,
        context: OperationContext,
        command: AssignTestCaseOwnersCommand,
    ) -> dict:
        """
        分配测试用例负责人（Phase 4显式命令）。

        这是Phase 4的核心实现：负责人分配必须通过显式命令，不能通过通用更新。

        Args:
            context: 操作上下文
            command: 分配测试用例负责人命令

        Returns:
            更新后的测试用例数据字典

        Raises:
            TestCaseNotFoundError: 测试用例不存在时抛出
            PermissionDeniedError: 没有更新权限时抛出
        """
        command.validate()
        test_case = await ensure_entity(
            command.case_id,
            self._test_case_service.get_test_case,
            TestCaseNotFoundError,
        )
        await ensure_permission(
            context,
            test_case,
            can_update_test_case,
            "assign test case owners",
            self._workflow_command_service.get_work_item_by_id,
        )

        return await self._test_case_service.assign_owners(
            case_id=command.case_id,
            owner_id=command.owner_id,
            reviewer_id=command.reviewer_id,
            auto_dev_id=command.auto_dev_id,
        )

    async def move_to_requirement(
        self,
        context: OperationContext,
        command: MoveTestCaseToRequirementCommand,
    ) -> dict:
        """
        将测试用例移动到不同需求（Phase 4显式命令）。

        这是Phase 4的核心实现：用例迁移必须通过显式命令，不能通过通用更新。

        Args:
            context: 操作上下文
            command: 移动测试用例命令

        Returns:
            更新后的测试用例数据字典

        Raises:
            TestCaseNotFoundError: 测试用例不存在时抛出
            RequirementNotFoundError: 目标需求不存在时抛出
            PermissionDeniedError: 没有更新权限时抛出
        """
        test_case = await ensure_entity(
            command.case_id,
            self._test_case_service.get_test_case,
            TestCaseNotFoundError,
        )

        if test_case.get("ref_req_id") == command.target_req_id:
            raise ValueError("test case is already linked to the target requirement")

        # 验证目标需求存在
        await ensure_entity(
            command.target_req_id,
            self._requirement_service.get_requirement,
            RequirementNotFoundError,
        )

        command.validate()
        await ensure_permission(
            context,
            test_case,
            can_update_test_case,
            "move test case to requirement",
            self._workflow_command_service.get_work_item_by_id,
        )

        return await self._test_case_service.move_to_requirement(
            case_id=command.case_id,
            target_req_id=command.target_req_id,
        )

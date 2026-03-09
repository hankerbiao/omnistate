from copy import deepcopy

from app.modules.test_specs.application.commands import (
    CreateRequirementCommand,
    DeleteRequirementCommand,
    UpdateRequirementCommand,
)
from app.modules.test_specs.domain.policies import can_delete_requirement, can_update_requirement
from app.modules.test_specs.service import RequirementService
from app.modules.workflow.application import DeleteWorkItemCommand, OperationContext, WorkflowCommandService
from app.modules.workflow.domain.exceptions import PermissionDeniedError


class RequirementCommandService:
    """
    需求命令服务类，负责处理需求的各种命令操作。

    该服务类封装了需求的创建、更新和删除操作，并与工作流服务集成，
    确保操作符合权限策略和业务规则。
    """

    def __init__(
        self,
        requirement_service: RequirementService,
        workflow_command_service: WorkflowCommandService,
    ):
        """
        初始化需求命令服务。

        Args:
            requirement_service: 需求服务实例，用于执行需求相关的数据库操作
            workflow_command_service: 工作流命令服务实例，用于处理工作流相关的操作
        """
        self._requirement_service = requirement_service
        self._workflow_command_service = workflow_command_service

    async def create_requirement(
        self,
        context: OperationContext,
        command: CreateRequirementCommand,
    ) -> dict:
        """
        创建新的需求。

        如果请求中没有指定tpm_owner_id，则默认将当前操作者设置为负责人。
        这确保每个需求都有一个明确的负责人。

        Args:
            context: 操作上下文，包含执行操作的用户信息
            command: 创建需求命令，包含需求的基本信息

        Returns:
            创建成功的需求数据字典

        Raises:
            相关异常可能由底层服务抛出
        """
        payload = deepcopy(command.payload)
        owner_id = str(payload.get("tpm_owner_id") or "").strip()
        if not owner_id:
            payload["tpm_owner_id"] = context.actor_id
        return await self._requirement_service.create_requirement(payload)

    async def update_requirement(
        self,
        context: OperationContext,
        command: UpdateRequirementCommand,
    ) -> dict:
        """
        更新现有需求。

        执行以下步骤：
        1. 验证更新字段不为空
        2. 获取需求信息并验证存在性
        3. 获取关联的工作流项（如果有）
        4. 检查更新权限
        5. 执行更新操作

        Args:
            context: 操作上下文，包含执行操作的用户信息
            command: 更新需求命令，包含需求ID和更新字段

        Returns:
            更新后的需求数据字典

        Raises:
            ValueError: 更新字段为空时抛出
            RequirementNotFoundError: 需求不存在时抛出
            PermissionDeniedError: 没有更新权限时抛出
        """
        if not command.payload:
            raise ValueError("no fields to update")

        requirement = await self._requirement_service.get_requirement(command.req_id)
        if not requirement:
            from app.modules.test_specs.domain.exceptions import RequirementNotFoundError
            raise RequirementNotFoundError(command.req_id)

        workflow_item_id = str(requirement.get("workflow_item_id") or "").strip()
        work_item = None
        if workflow_item_id:
            from app.modules.workflow.service.workflow_service import AsyncWorkflowService
            workflow_service = AsyncWorkflowService()
            work_item = await workflow_service.get_item_by_id(workflow_item_id)

        actor = {"actor_id": context.actor_id, "role_ids": context.role_ids}
        if not can_update_requirement(actor, requirement, work_item):
            raise PermissionDeniedError(context.actor_id, "update requirement")

        return await self._requirement_service.update_requirement(command.req_id, command.payload)

    async def delete_requirement(
        self,
        context: OperationContext,
        command: DeleteRequirementCommand,
    ) -> None:
        """
        删除需求。

        执行以下步骤：
        1. 获取需求信息并验证存在性
        2. 获取关联的工作流项（如果有）
        3. 检查删除权限
        4. 如果有关联工作流项，先删除工作流项
        5. 否则直接删除需求

        Args:
            context: 操作上下文，包含执行操作的用户信息
            command: 删除需求命令，包含要删除的需求ID

        Raises:
            RequirementNotFoundError: 需求不存在时抛出
            PermissionDeniedError: 没有删除权限时抛出
        """
        requirement = await self._requirement_service.get_requirement(command.req_id)
        if not requirement:
            from app.modules.test_specs.domain.exceptions import RequirementNotFoundError
            raise RequirementNotFoundError(command.req_id)

        workflow_item_id = str(requirement.get("workflow_item_id") or "").strip()
        work_item = None
        if workflow_item_id:
            from app.modules.workflow.service.workflow_service import AsyncWorkflowService
            workflow_service = AsyncWorkflowService()
            work_item = await workflow_service.get_item_by_id(workflow_item_id)

        actor = {"actor_id": context.actor_id, "role_ids": context.role_ids}
        if not can_delete_requirement(actor, requirement, work_item):
            raise PermissionDeniedError(context.actor_id, "delete requirement")

        if workflow_item_id:
            await self._workflow_command_service.delete_work_item(
                context,
                DeleteWorkItemCommand(work_item_id=workflow_item_id),
            )
            return
        await self._requirement_service.delete_requirement(command.req_id)

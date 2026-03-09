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
    def __init__(
        self,
        requirement_service: RequirementService,
        workflow_command_service: WorkflowCommandService,
    ):
        self._requirement_service = requirement_service
        self._workflow_command_service = workflow_command_service

    async def create_requirement(
        self,
        context: OperationContext,
        command: CreateRequirementCommand,
    ) -> dict:
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
            work_item = await workflow_service.get_item(workflow_item_id)

        actor = {"actor_id": context.actor_id, "role_ids": context.role_ids}
        if not can_update_requirement(actor, requirement, work_item):
            raise PermissionDeniedError(context.actor_id, "update requirement")

        return await self._requirement_service.update_requirement(command.req_id, command.payload)

    async def delete_requirement(
        self,
        context: OperationContext,
        command: DeleteRequirementCommand,
    ) -> None:
        requirement = await self._requirement_service.get_requirement(command.req_id)
        if not requirement:
            from app.modules.test_specs.domain.exceptions import RequirementNotFoundError
            raise RequirementNotFoundError(command.req_id)

        workflow_item_id = str(requirement.get("workflow_item_id") or "").strip()
        work_item = None
        if workflow_item_id:
            from app.modules.workflow.service.workflow_service import AsyncWorkflowService
            workflow_service = AsyncWorkflowService()
            work_item = await workflow_service.get_item(workflow_item_id)

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

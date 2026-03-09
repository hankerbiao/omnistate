from app.modules.workflow.application.commands import (
    CreateWorkItemCommand,
    DeleteWorkItemCommand,
    ReassignWorkItemCommand,
    TransitionWorkItemCommand,
)
from app.modules.workflow.application.contexts import OperationContext
from app.modules.workflow.service.workflow_service import AsyncWorkflowService


class WorkflowCommandService:
    def __init__(self, workflow_service: AsyncWorkflowService):
        self._workflow_service = workflow_service

    async def create_work_item(
        self,
        context: OperationContext,
        command: CreateWorkItemCommand,
    ) -> dict:
        return await self._workflow_service.create_item(
            type_code=command.type_code,
            title=command.title,
            content=command.content,
            creator_id=context.actor_id,
            parent_item_id=command.parent_item_id,
        )

    async def transition_work_item(
        self,
        context: OperationContext,
        command: TransitionWorkItemCommand,
    ) -> dict:
        return await self._workflow_service.handle_transition(
            work_item_id=command.work_item_id,
            action=command.action,
            operator_id=context.actor_id,
            form_data=command.form_data,
            actor_role_ids=context.role_ids,
        )

    async def reassign_work_item(
        self,
        context: OperationContext,
        command: ReassignWorkItemCommand,
    ) -> dict:
        return await self._workflow_service.reassign_item(
            item_id=command.work_item_id,
            operator_id=context.actor_id,
            target_owner_id=command.target_owner_id,
            remark=command.remark,
            actor_role_ids=context.role_ids,
        )

    async def delete_work_item(
        self,
        context: OperationContext,
        command: DeleteWorkItemCommand,
    ) -> bool:
        return await self._workflow_service.delete_item(
            item_id=command.work_item_id,
            operator_id=context.actor_id,
            actor_role_ids=context.role_ids,
        )

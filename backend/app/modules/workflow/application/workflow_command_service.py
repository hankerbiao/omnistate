from app.modules.workflow.application.commands import (
    CreateWorkItemCommand,
    DeleteWorkItemCommand,
    ReassignWorkItemCommand,
    TransitionWorkItemCommand,
)
from app.modules.workflow.application.contexts import OperationContext
from app.modules.workflow.application.ports import WorkflowMutationHook
from app.modules.workflow.application.query_service import WorkflowQueryService
from app.modules.workflow.application.mutation_service import WorkflowMutationService
from app.modules.workflow.service.workflow_service import AsyncWorkflowService


class WorkflowCommandService:
    def __init__(
        self,
        workflow_service: AsyncWorkflowService | WorkflowMutationService,
        query_service: WorkflowQueryService | None = None,
        mutation_hooks: list[WorkflowMutationHook] | None = None,
    ):
        self._workflow_service = workflow_service
        self._query_service = query_service
        self._mutation_hooks = mutation_hooks or []

    async def _run_hook(self, method_name: str, payload: dict) -> None:
        for hook in self._mutation_hooks:
            method = getattr(hook, method_name, None)
            if method is None:
                continue
            await method(payload)

    async def get_work_item_by_id(self, item_id: str) -> dict | None:
        if hasattr(self._workflow_service, "get_item_by_id"):
            return await self._workflow_service.get_item_by_id(item_id)
        if self._query_service is None:
            raise RuntimeError("query_service is required to load work items for command hooks")
        return await self._query_service.get_item_by_id(item_id)

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
        result = await self._workflow_service.handle_transition(
            work_item_id=command.work_item_id,
            action=command.action,
            operator_id=context.actor_id,
            form_data=command.form_data,
            actor_role_ids=context.role_ids,
        )
        await self._run_hook("after_transition", result)
        return result

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
        work_item = await self._workflow_service.get_item_by_id(command.work_item_id)
        if work_item is not None:
            await self._run_hook("before_delete", work_item)

        deleted = await self._workflow_service.delete_item(
            item_id=command.work_item_id,
            operator_id=context.actor_id,
            actor_role_ids=context.role_ids,
        )
        if deleted and work_item is not None:
            await self._run_hook("after_delete", work_item)
        return deleted

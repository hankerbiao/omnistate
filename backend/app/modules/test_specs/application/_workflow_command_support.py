from typing import Any, Awaitable, Callable

from app.modules.workflow.application import DeleteWorkItemCommand, OperationContext, WorkflowCommandService
from app.modules.workflow.domain.exceptions import PermissionDeniedError
from app.modules.workflow.service.workflow_service import AsyncWorkflowService


def build_actor(context: OperationContext) -> dict[str, Any]:
    return {"actor_id": context.actor_id, "role_ids": context.role_ids}


async def ensure_entity(
    entity_id: str,
    getter: Callable[[str], Awaitable[dict]],
    error_cls: type[Exception],
) -> dict:
    try:
        return await getter(entity_id)
    except KeyError as exc:
        raise error_cls(entity_id) from exc


async def get_work_item(entity: dict) -> tuple[str, Any]:
    workflow_item_id = str(entity.get("workflow_item_id") or "").strip()
    if not workflow_item_id:
        return workflow_item_id, None
    return workflow_item_id, await AsyncWorkflowService().get_item_by_id(workflow_item_id)


async def ensure_permission(
    context: OperationContext,
    entity: dict,
    checker: Callable[[dict[str, Any], dict, Any], bool],
    action: str,
) -> str:
    workflow_item_id, work_item = await get_work_item(entity)
    if not checker(build_actor(context), entity, work_item):
        raise PermissionDeniedError(context.actor_id, action)
    return workflow_item_id


async def delete_entity_or_work_item(
    context: OperationContext,
    workflow_command_service: WorkflowCommandService,
    workflow_item_id: str,
    delete_fn: Callable[[], Awaitable[None]],
) -> None:
    if workflow_item_id:
        await workflow_command_service.delete_work_item(
            context,
            DeleteWorkItemCommand(work_item_id=workflow_item_id),
        )
        return
    await delete_fn()

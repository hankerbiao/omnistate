from typing import Any, Awaitable, Callable

from app.modules.workflow.application import DeleteWorkItemCommand, OperationContext, WorkflowCommandService
from app.modules.workflow.domain.exceptions import PermissionDeniedError
from app.modules.workflow.service.workflow_service import AsyncWorkflowService


def build_actor(context: OperationContext) -> dict[str, Any]:
    """把操作上下文转换成策略函数使用的 actor 结构。"""
    return {"actor_id": context.actor_id, "role_ids": context.role_ids}


async def ensure_entity(
    entity_id: str,
    getter: Callable[[str], Awaitable[dict]],
    error_cls: type[Exception],
) -> dict:
    """统一把 service 的 KeyError 转成领域异常，收敛重复样板代码。"""
    try:
        return await getter(entity_id)
    except KeyError as exc:
        raise error_cls(entity_id) from exc


async def get_work_item(entity: dict) -> tuple[str, Any]:
    """按业务实体里的 workflow_item_id 加载关联工作项。"""
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
    """统一执行 workflow-aware 权限判断，并返回 workflow_item_id 供后续复用。"""
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
    """优先走 workflow 删除路径；无工作项时回退到业务文档删除。"""
    if workflow_item_id:
        await workflow_command_service.delete_work_item(
            context,
            DeleteWorkItemCommand(work_item_id=workflow_item_id),
        )
        return
    await delete_fn()

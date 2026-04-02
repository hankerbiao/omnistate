from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.workflow.api.dependencies import (
    WorkflowCommandServiceDep,
    WorkflowQueryServiceDep,
    build_operation_context,
)
from app.modules.workflow.application import (
    DeleteWorkItemCommand,
    ReassignWorkItemCommand,
    TransitionWorkItemCommand,
)
from app.modules.workflow.domain.exceptions import (
    InvalidTransitionError,
    MissingRequiredFieldError,
    PermissionDeniedError,
    WorkItemNotFoundError,
)
from app.modules.workflow.schemas.work_item import (
    AvailableTransitionResponse,
    AvailableTransitionsResponse,
    DeleteWorkItemData,
    TransitionLogResponse,
    TransitionRequest,
    TransitionResponse,
    WorkItemResponse,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.api.schemas.error import ErrorResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter()


@router.delete(
    "/{item_id}",
    response_model=APIResponse[DeleteWorkItemData],
    summary="删除事项",
    dependencies=[Depends(require_permission("work_items:write"))],
    responses={
        404: {"model": APIResponse[ErrorResponse], "description": "事项不存在"},
        400: {"model": APIResponse[ErrorResponse], "description": "删除失败"},
    },
)
async def delete_work_item(
    item_id: str,
    command_service: WorkflowCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        await command_service.delete_work_item(
            build_operation_context(current_user),
            DeleteWorkItemCommand(work_item_id=item_id),
        )
        return APIResponse(message="deleted", data=DeleteWorkItemData(item_id=item_id))
    except WorkItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"删除失败: {str(exc)}")


@router.post(
    "/{item_id}/transition",
    response_model=APIResponse[TransitionResponse],
    summary="执行状态流转",
    dependencies=[Depends(require_permission("work_items:transition"))],
    responses={
        404: {"model": APIResponse[ErrorResponse], "description": "事项不存在"},
        400: {"model": APIResponse[ErrorResponse], "description": "流转失败"},
    },
)
async def transition_work_item(
    item_id: str,
    request: TransitionRequest,
    command_service: WorkflowCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        result = await command_service.transition_work_item(
            build_operation_context(current_user),
            TransitionWorkItemCommand(
                work_item_id=item_id,
                action=request.action,
                form_data=request.form_data,
            ),
        )
        return APIResponse(data=result)
    except WorkItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except (InvalidTransitionError, MissingRequiredFieldError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/{item_id}/reassign",
    response_model=APIResponse[WorkItemResponse],
    summary="改派任务",
    dependencies=[Depends(require_permission("work_items:write"))],
    responses={
        404: {"model": APIResponse[ErrorResponse], "description": "事项不存在"},
        400: {"model": APIResponse[ErrorResponse], "description": "改派失败"},
    },
)
async def reassign_work_item(
    item_id: str,
    command_service: WorkflowCommandServiceDep,
    target_owner_id: str = Query(..., description="目标处理人ID"),
    remark: str | None = Query(None, description="备注信息（非必填）"),
    current_user=Depends(get_current_user),
):
    try:
        data = await command_service.reassign_work_item(
            build_operation_context(current_user),
            ReassignWorkItemCommand(
                work_item_id=item_id,
                target_owner_id=target_owner_id,
                remark=remark,
            ),
        )
        return APIResponse(data=data)
    except WorkItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"改派失败: {str(exc)}")


@router.get(
    "/{item_id}/logs",
    response_model=APIResponse[list[TransitionLogResponse]],
    summary="获取流转历史",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def get_transition_logs(
    item_id: str,
    service: WorkflowQueryServiceDep,
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
):
    try:
        return APIResponse(data=await service.get_logs(item_id, limit))
    except WorkItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/logs/batch",
    response_model=APIResponse[dict[str, list[TransitionLogResponse]]],
    summary="批量获取事项流转日志",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def batch_get_transition_logs(
    service: WorkflowQueryServiceDep,
    item_ids: str = Query(..., description="事项ID列表，逗号分隔，如: id1,id2,id3"),
    limit: int = Query(20, ge=1, le=100, description="每个事项最多返回的日志数量"),
):
    ids = [item.strip() for item in item_ids.split(",") if item.strip()]
    if not ids:
        return APIResponse(data={})
    try:
        return APIResponse(data=await service.batch_get_logs(ids, limit))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/{item_id}/transitions",
    response_model=APIResponse[AvailableTransitionsResponse],
    summary="获取可用的下一步流转",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def get_available_transitions(item_id: str, service: WorkflowQueryServiceDep):
    try:
        result = await service.get_item_with_transitions(item_id)
        item = result["item"]
        return APIResponse(
            data=AvailableTransitionsResponse(
                item_id=item_id,
                current_state=item["current_state"],
                available_transitions=[
                    AvailableTransitionResponse(**transition)
                    for transition in result["available_transitions"]
                ],
            )
        )
    except WorkItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

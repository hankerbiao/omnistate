from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.workflow.api.dependencies import (
    WorkflowCommandServiceDep,
    WorkflowQueryServiceDep,
    build_operation_context,
)
from app.modules.workflow.application import CreateWorkItemCommand
from app.modules.workflow.schemas.work_item import CreateWorkItemRequest, WorkItemResponse
from app.shared.api.schemas.base import APIResponse
from app.shared.api.schemas.error import ErrorResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter()


@router.post(
    "",
    response_model=APIResponse[WorkItemResponse],
    status_code=201,
    summary="创建业务事项",
    dependencies=[Depends(require_permission("work_items:write"))],
)
async def create_work_item(
    request: CreateWorkItemRequest,
    command_service: WorkflowCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        item = await command_service.create_work_item(
            build_operation_context(current_user),
            CreateWorkItemCommand(
                type_code=request.type_code,
                title=request.title,
                content=request.content,
                parent_item_id=str(request.parent_item_id) if request.parent_item_id else None,
            ),
        )
        return APIResponse(data=item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "",
    response_model=APIResponse[list[WorkItemResponse]],
    summary="获取事项列表",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def list_work_items(
    service: WorkflowQueryServiceDep,
    type_code: Optional[str] = Query(None, description="按类型筛选"),
    state: Optional[str] = Query(None, description="按状态筛选"),
    owner_id: Optional[str] = Query(None, description="按当前处理人筛选"),
    creator_id: Optional[str] = Query(None, description="按创建人筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
):
    return APIResponse(
        data=await service.list_items(type_code, state, owner_id, creator_id, limit, offset)
    )


@router.get(
    "/sorted",
    response_model=APIResponse[list[WorkItemResponse]],
    summary="获取排序后的事项列表",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def list_work_items_sorted(
    service: WorkflowQueryServiceDep,
    type_code: Optional[str] = Query(None, description="按类型筛选"),
    state: Optional[str] = Query(None, description="按状态筛选"),
    owner_id: Optional[str] = Query(None, description="按当前处理人筛选"),
    creator_id: Optional[str] = Query(None, description="按创建人筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    order_by: str = Query("created_at", description="排序字段: created_at/updated_at/title"),
    direction: str = Query("desc", description="排序方向: asc/desc"),
):
    return APIResponse(
        data=await service.list_items_sorted(
            type_code, state, owner_id, creator_id, limit, offset, order_by, direction
        )
    )


@router.get(
    "/search",
    response_model=APIResponse[list[WorkItemResponse]],
    summary="模糊搜索事项",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def search_work_items(
    service: WorkflowQueryServiceDep,
    keyword: str = Query(..., min_length=2, max_length=100, description="关键词，搜索标题和内容"),
    type_code: Optional[str] = Query(None, description="按类型筛选"),
    state: Optional[str] = Query(None, description="按状态筛选"),
    owner_id: Optional[str] = Query(None, description="按当前处理人筛选"),
    creator_id: Optional[str] = Query(None, description="按创建人筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
):
    return APIResponse(
        data=await service.search_items(keyword, type_code, state, owner_id, creator_id, limit, offset)
    )


@router.get(
    "/{item_id}",
    response_model=APIResponse[WorkItemResponse],
    summary="获取事项详情",
    dependencies=[Depends(require_permission("work_items:read"))],
    responses={404: {"model": APIResponse[ErrorResponse], "description": "事项不存在"}},
)
async def get_work_item(item_id: str, service: WorkflowQueryServiceDep):
    try:
        item = await service.get_item_by_id(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"事项 ID={item_id} 不存在")
        return APIResponse(data=item)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

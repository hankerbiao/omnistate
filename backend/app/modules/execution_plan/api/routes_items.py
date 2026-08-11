"""Execution plan item query and mutation routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.execution_plan.api._route_support import (
    READ_DEP,
    WRITE_DEP,
    _resolve_assignee_id,
    get_user_id,
)
from app.modules.execution_plan.api.dependencies import PlanCommandServiceDep, PlanQueryServiceDep
from app.modules.execution_plan.api.exception_handler import handle_service_error
from app.modules.execution_plan.schemas.execution_plan import (
    AddPlanItemsRequest,
    BatchUpdateAssigneeRequest,
    ReassignRequest,
    UpdatePlanItemRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter()


@router.get(
    "/items/my-items",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="获取当前用户的计划任务列表（My Tasks）",
    dependencies=READ_DEP,
)
async def list_my_plan_items(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    assignee_id: Optional[str] = Query(None, description="执行人 user_id，不传则默认当前用户"),
    limit: int = Query(200, ge=1, le=1000, description="返回条目数量上限"),
):
    uid = _resolve_assignee_id(current_user, assignee_id)
    return APIResponse(data=await query_service.list_my_items(uid, limit=limit))


@router.get(
    "/items",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="查询计划条目列表（支持状态/计划筛选，不限执行人）",
    dependencies=READ_DEP,
)
async def list_plan_items(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="按状态筛选: pending|running|done|fail"),
    plan_id: Optional[str] = Query(None, description="按计划ID筛选"),
    limit: int = Query(200, description="返回条目数量上限", ge=1, le=1000),
):
    items = await query_service.list_items(status=status, plan_id=plan_id, limit=limit)
    return APIResponse(data=items)


@router.get(
    "/items/overview",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取所有计划的运行总览",
    dependencies=READ_DEP,
)
async def get_plan_overview(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return APIResponse(data=await query_service.get_overview())


@router.get(
    "/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取单条计划条目详情",
    dependencies=READ_DEP,
)
async def get_plan_item(
    item_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        return APIResponse(data=await query_service.get_item(item_id))
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="更新计划条目（状态/指派人等）",
    dependencies=WRITE_DEP,
)
async def update_plan_item(
    plan_id: str,
    item_id: str,
    data: UpdatePlanItemRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        item = await command_service.update_item(
            plan_id=plan_id,
            item_id=item_id,
            data=data.model_dump(exclude_none=True),
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=item)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/reassign",
    response_model=APIResponse[Dict[str, Any]],
    summary="改派计划条目执行人",
    dependencies=WRITE_DEP,
)
async def reassign_plan_item(
    item_id: str,
    request: ReassignRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        result = await command_service.reassign_item(
            item_id=item_id,
            assignee_id=request.assignee_id,
            operator_id=get_user_id(current_user),
            remark=request.remark,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/plans/{plan_id}/items",
    status_code=201,
    summary="为计划添加条目",
    dependencies=WRITE_DEP,
)
async def add_plan_items(
    plan_id: str,
    request: AddPlanItemsRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        plan = await command_service.add_items(
            plan_id=plan_id,
            items_data=[item.model_dump() for item in request.items],
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.delete(
    "/plans/{plan_id}/items/{item_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="从计划中移除条目（软删除）",
    dependencies=WRITE_DEP,
)
async def delete_plan_item(
    plan_id: str,
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        await command_service.delete_item(
            plan_id=plan_id,
            item_id=item_id,
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data={"plan_id": plan_id, "item_id": item_id, "deleted": True})
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}/items/batch-assignee",
    response_model=APIResponse[Dict[str, Any]],
    summary="批量更新计划条目执行人",
    dependencies=WRITE_DEP,
)
async def batch_update_assignee(
    plan_id: str,
    request: BatchUpdateAssigneeRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        result = await command_service.batch_update_assignee(
            plan_id=plan_id,
            item_ids=request.item_ids,
            assignee_id=request.assignee_id,
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)

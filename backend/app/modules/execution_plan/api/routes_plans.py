"""Execution plan CRUD routes."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.execution_plan.api._route_support import READ_DEP, WRITE_DEP, get_user_id
from app.modules.execution_plan.api.dependencies import PlanCommandServiceDep, PlanQueryServiceDep
from app.modules.execution_plan.api.exception_handler import handle_service_error
from app.modules.execution_plan.schemas.execution_plan import CreatePlanRequest, UpdatePlanRequest
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter()


@router.get(
    "/plans",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取执行计划列表（分页）",
    dependencies=READ_DEP,
)
async def list_plans(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = Query(None, description="按状态筛选: active|done"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    plans = await query_service.list_plans(status=status, page=page, page_size=page_size)
    return APIResponse(data=plans)


@router.post(
    "/plans",
    response_model=APIResponse[Dict[str, Any]],
    status_code=201,
    summary="创建执行计划",
    dependencies=WRITE_DEP,
)
async def create_plan(
    request: CreatePlanRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        plan = await command_service.create_plan(
            data=request.model_dump(exclude_none=True),
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取执行计划详情（含条目列表）",
    dependencies=READ_DEP,
)
async def get_plan_detail(
    plan_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        return APIResponse(data=await query_service.get_plan(plan_id=plan_id))
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="更新执行计划",
    dependencies=WRITE_DEP,
)
async def update_plan(
    plan_id: str,
    request: UpdatePlanRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        plan = await command_service.update_plan(
            plan_id=plan_id,
            data=request.model_dump(exclude_none=True),
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=plan)
    except Exception as exc:
        handle_service_error(exc)


@router.delete(
    "/plans/{plan_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="删除执行计划（软删除）",
    dependencies=WRITE_DEP,
)
async def delete_plan(
    plan_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        await command_service.delete_plan(plan_id=plan_id, actor_id=get_user_id(current_user))
        return APIResponse(data={"plan_id": plan_id, "deleted": True})
    except Exception as exc:
        handle_service_error(exc)

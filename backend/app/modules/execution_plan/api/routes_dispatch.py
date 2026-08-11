"""Execution plan dispatch and rerun routes."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.modules.execution_plan.api._route_support import WRITE_DEP, get_user_id
from app.modules.execution_plan.api.dependencies import PlanCommandServiceDep
from app.modules.execution_plan.api.exception_handler import handle_service_error
from app.modules.execution_plan.schemas.execution_plan import (
    BatchDispatchRequest,
    PlanItemDispatchRequest,
    PlanItemRerunRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter()


@router.post(
    "/items/{item_id}/dispatch",
    response_model=APIResponse[Dict[str, Any]],
    summary="单条自动化用例计划内下发",
    dependencies=WRITE_DEP,
)
async def dispatch_single_item(
    item_id: str,
    request: PlanItemDispatchRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        result = await command_service.dispatch_plan_item(
            item_id=item_id,
            request=request,
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/cancel-execution",
    response_model=APIResponse[Dict[str, Any]],
    summary="取消自动化条目的执行",
    dependencies=WRITE_DEP,
)
async def cancel_item_execution(
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        result = await command_service.cancel_execution(
            item_id=item_id,
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/{item_id}/rerun",
    response_model=APIResponse[Dict[str, Any]],
    status_code=201,
    summary="重新执行计划条目",
    dependencies=WRITE_DEP,
)
async def rerun_plan_item(
    item_id: str,
    request: PlanItemRerunRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        result = await command_service.rerun_item(
            item_id=item_id,
            actor_id=get_user_id(current_user),
            request=request,
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.post(
    "/items/batch-dispatch",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="批量下发自动化用例",
    dependencies=WRITE_DEP,
)
async def batch_dispatch_items(
    request: BatchDispatchRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        results = await command_service.batch_dispatch(
            request=request,
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=results)
    except Exception as exc:
        handle_service_error(exc)

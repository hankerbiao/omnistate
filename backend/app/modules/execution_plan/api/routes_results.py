"""Execution plan result routes."""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.modules.execution_plan.api._route_support import READ_DEP, WRITE_DEP, get_user_id
from app.modules.execution_plan.api.dependencies import PlanCommandServiceDep, PlanQueryServiceDep
from app.modules.execution_plan.api.exception_handler import handle_service_error
from app.modules.execution_plan.schemas.execution_plan import SubmitManualResultRequest
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter()


@router.post(
    "/items/{item_id}/result",
    response_model=APIResponse[Dict[str, Any]],
    summary="提交手工测试结果回填",
    dependencies=WRITE_DEP,
)
async def submit_manual_result(
    item_id: str,
    request: SubmitManualResultRequest,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        result = await command_service.submit_manual_result(
            item_id=item_id,
            request=request,
            actor_id=get_user_id(current_user),
        )
        return APIResponse(data=result)
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/items/{item_id}/result",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取已有的手工结果回填",
    dependencies=READ_DEP,
)
async def get_manual_result(
    item_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        return APIResponse(data=await query_service.get_result(item_id=item_id))
    except Exception as exc:
        handle_service_error(exc)


@router.get(
    "/cases/{case_id}/execution-stats",
    response_model=APIResponse[Dict[str, Any]],
    summary="获取测试用例的执行统计",
    dependencies=READ_DEP,
)
async def get_case_execution_stats(
    case_id: str,
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return APIResponse(data=await query_service.get_case_execution_stats(case_id))

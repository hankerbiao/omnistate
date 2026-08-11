"""Execution plan archive routes."""

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
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter()


@router.get(
    "/items/archived",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="获取已归档的计划任务列表（收纳箱）",
    dependencies=READ_DEP,
)
async def list_archived_items(
    query_service: PlanQueryServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
    assignee_id: Optional[str] = Query(None, description="执行人 user_id，不传则默认当前用户"),
    limit: int = Query(200, ge=1, le=1000, description="返回条目数量上限"),
):
    uid = _resolve_assignee_id(current_user, assignee_id)
    return APIResponse(data=await query_service.list_archived_items(uid, limit=limit))


@router.put(
    "/items/{item_id}/archive",
    response_model=APIResponse[Dict[str, Any]],
    summary="归档计划条目（收纳）",
    dependencies=WRITE_DEP,
)
async def archive_item(
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        await command_service.archive_item(item_id=item_id, actor_id=get_user_id(current_user))
        return APIResponse(data={"item_id": item_id, "archived": True})
    except Exception as exc:
        handle_service_error(exc)


@router.put(
    "/items/{item_id}/unarchive",
    response_model=APIResponse[Dict[str, Any]],
    summary="取消归档计划条目",
    dependencies=WRITE_DEP,
)
async def unarchive_item(
    item_id: str,
    command_service: PlanCommandServiceDep,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        await command_service.unarchive_item(item_id=item_id, actor_id=get_user_id(current_user))
        return APIResponse(data={"item_id": item_id, "archived": False})
    except Exception as exc:
        handle_service_error(exc)

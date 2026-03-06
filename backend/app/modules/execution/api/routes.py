"""测试执行 API 路由。"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.modules.execution.schemas import (
    DispatchTaskRequest,
    DispatchTaskResponse,
)
from app.modules.execution.service import ExecutionService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/execution", tags=["Execution"])


def get_execution_service() -> ExecutionService:
    return ExecutionService()


ExecutionServiceDep = Annotated[ExecutionService, Depends(get_execution_service)]


@router.post(
    "/tasks/dispatch",
    response_model=APIResponse[DispatchTaskResponse],
    status_code=201,
    summary="下发测试任务",
    dependencies=[Depends(require_permission("execution_tasks:write"))],
)
async def dispatch_task(
        request: DispatchTaskRequest,
        service: ExecutionServiceDep,
        current_user=Depends(get_current_user),
):
    try:
        data = await service.dispatch_task(request.model_dump(), created_by=current_user["user_id"])
        return APIResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

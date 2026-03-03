"""测试执行 API 路由。"""
from __future__ import annotations

import json
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.modules.execution.schemas import (
    DispatchTaskRequest,
    DispatchTaskResponse,
    ExecutionTaskCaseResponse,
    ExecutionTaskResponse,
    ProgressCallbackRequest,
    ProgressCallbackResponse,
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


@router.get(
    "/tasks/{task_id}",
    response_model=APIResponse[ExecutionTaskResponse],
    summary="查询任务详情",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_task(task_id: str, service: ExecutionServiceDep):
    try:
        data = await service.get_task(task_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")


@router.get(
    "/tasks",
    response_model=APIResponse[List[ExecutionTaskResponse]],
    summary="查询任务列表",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def list_tasks(
    service: ExecutionServiceDep,
    created_by: Optional[str] = Query(None),
    framework: Optional[str] = Query(None),
    overall_status: Optional[str] = Query(None),
    dispatch_status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await service.list_tasks(
        created_by=created_by,
        framework=framework,
        overall_status=overall_status,
        dispatch_status=dispatch_status,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.get(
    "/tasks/{task_id}/cases",
    response_model=APIResponse[List[ExecutionTaskCaseResponse]],
    summary="查询任务用例明细",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def list_task_cases(
    task_id: str,
    service: ExecutionServiceDep,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    try:
        data = await service.list_task_cases(task_id=task_id, status=status, limit=limit, offset=offset)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")


@router.post(
    "/callbacks/progress",
    response_model=APIResponse[ProgressCallbackResponse],
    summary="接收测试框架进度回报",
)
async def callback_progress(
    req: Request,
    body: ProgressCallbackRequest,
    service: ExecutionServiceDep,
):
    raw_body = await req.body()
    if not raw_body:
        raw_body = json.dumps(body.model_dump(mode="json", by_alias=True), ensure_ascii=False).encode("utf-8")

    headers = {
        "x-framework-id": req.headers.get("x-framework-id", ""),
        "x-event-id": req.headers.get("x-event-id", ""),
        "x-timestamp": req.headers.get("x-timestamp", ""),
        "x-signature": req.headers.get("x-signature", ""),
    }

    try:
        data = await service.handle_progress_callback(
            headers=headers,
            raw_body=raw_body,
            payload=body.model_dump(mode="json"),
        )
        return APIResponse(data=data)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

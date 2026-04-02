from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.workflow.api.dependencies import WorkflowQueryServiceDep
from app.modules.workflow.schemas.workflow import (
    WorkTypeResponse,
    WorkflowConfigResponse,
    WorkflowStateResponse,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.api.schemas.error import ErrorResponse
from app.shared.auth import require_permission

router = APIRouter()


@router.get(
    "/types",
    response_model=APIResponse[list[WorkTypeResponse]],
    summary="获取事项类型列表",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def get_work_types(service: WorkflowQueryServiceDep):
    return APIResponse(data=await service.get_work_types())


@router.get(
    "/states",
    response_model=APIResponse[list[WorkflowStateResponse]],
    summary="获取流程状态列表",
    dependencies=[Depends(require_permission("work_items:read"))],
)
async def get_workflow_states(service: WorkflowQueryServiceDep):
    return APIResponse(data=await service.get_workflow_states())


@router.get(
    "/configs",
    response_model=APIResponse[list[WorkflowConfigResponse]],
    summary="获取指定类型的所有流转配置",
    dependencies=[Depends(require_permission("work_items:read"))],
    responses={404: {"model": APIResponse[ErrorResponse], "description": "类型不存在"}},
)
async def get_workflow_configs(
    service: WorkflowQueryServiceDep,
    type_code: str = Query(..., description="事项类型编码"),
):
    configs = await service.get_workflow_configs(type_code)
    if not configs:
        raise HTTPException(status_code=404, detail=f"类型 '{type_code}' 的流转配置不存在")
    return APIResponse(data=configs)

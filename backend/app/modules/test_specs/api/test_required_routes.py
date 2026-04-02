"""测试需求 API 路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.api.dependencies import (
    RequirementCommandServiceDep,
    RequirementQueryServiceDep,
    build_operation_context,
)
from app.modules.test_specs.application import (
    CreateRequirementCommand,
    DeleteRequirementCommand,
    UpdateRequirementCommand,
)
from app.modules.test_specs.schemas import (
    CreateRequirementRequest,
    RequirementResponse,
    UpdateRequirementRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/requirements", tags=["Requirements"])


@router.post(
    "",
    response_model=APIResponse[RequirementResponse],
    status_code=201,
    summary="创建测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def create_requirement(
    request: CreateRequirementRequest,
    command_service: RequirementCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        data = await command_service.create_requirement(
            build_operation_context(current_user),
            CreateRequirementCommand(payload=request.model_dump()),
        )
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/{req_id}",
    response_model=APIResponse[RequirementResponse],
    summary="获取测试需求详情",
    dependencies=[Depends(require_permission("requirements:read"))],
)
async def get_requirement(
    req_id: str,
    query_service: RequirementQueryServiceDep,
):
    try:
        data = await query_service.get_requirement(req_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.get(
    "",
    response_model=APIResponse[List[RequirementResponse]],
    summary="查询测试需求列表",
    dependencies=[Depends(require_permission("requirements:read"))],
)
async def list_requirements(
    query_service: RequirementQueryServiceDep,
    status: Optional[str] = Query(None),
    tpm_owner_id: Optional[str] = Query(None),
    manual_dev_id: Optional[str] = Query(None),
    auto_dev_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await query_service.list_requirements(
        status=status,
        tpm_owner_id=tpm_owner_id,
        manual_dev_id=manual_dev_id,
        auto_dev_id=auto_dev_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.put(
    "/{req_id}",
    response_model=APIResponse[RequirementResponse],
    summary="更新测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def update_requirement(
    req_id: str,
    request: UpdateRequirementRequest,
    command_service: RequirementCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        data = await command_service.update_requirement(
            build_operation_context(current_user),
            UpdateRequirementCommand(
                req_id=req_id,
                payload=request.model_dump(exclude_unset=True),
            ),
        )
        return APIResponse(data=data)
    except ValueError as e:
        if str(e) == "no fields to update":
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.delete(
    "/{req_id}",
    response_model=APIResponse[dict],
    summary="删除测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def delete_requirement(
    req_id: str,
    command_service: RequirementCommandServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        await command_service.delete_requirement(
            build_operation_context(current_user),
            DeleteRequirementCommand(req_id=req_id),
        )
        return APIResponse(data={"deleted": True})
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")

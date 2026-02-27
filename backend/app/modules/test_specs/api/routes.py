"""测试需求 API 路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.modules.test_specs.service import RequirementService
from app.modules.test_specs.schemas import (
    CreateRequirementRequest,
    UpdateRequirementRequest,
    RequirementResponse,
)

router = APIRouter(prefix="/requirements", tags=["Requirements"])


def get_requirement_service() -> RequirementService:
    return RequirementService()


RequirementServiceDep = Annotated[RequirementService, Depends(get_requirement_service)]


@router.post(
    "",
    response_model=APIResponse[RequirementResponse],
    status_code=201,
    summary="创建测试需求",
)
async def create_requirement(
    request: CreateRequirementRequest,
    service: RequirementServiceDep,
):
    try:
        data = await service.create_requirement(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/{req_id}",
    response_model=APIResponse[RequirementResponse],
    summary="获取测试需求详情",
)
async def get_requirement(
    req_id: str,
    service: RequirementServiceDep,
):
    try:
        data = await service.get_requirement(req_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.get(
    "",
    response_model=APIResponse[List[RequirementResponse]],
    summary="查询测试需求列表",
)
async def list_requirements(
    service: RequirementServiceDep,
    status: Optional[str] = Query(None),
    tpm_owner_id: Optional[str] = Query(None),
    manual_dev_id: Optional[str] = Query(None),
    auto_dev_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await service.list_requirements(
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
)
async def update_requirement(
    req_id: str,
    request: UpdateRequirementRequest,
    service: RequirementServiceDep,
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_requirement(req_id, payload)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")


@router.delete(
    "/{req_id}",
    response_model=APIResponse[dict],
    summary="删除测试需求",
)
async def delete_requirement(
    req_id: str,
    service: RequirementServiceDep,
):
    try:
        await service.delete_requirement(req_id)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")

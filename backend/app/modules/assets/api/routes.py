"""硬件与资产管理路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.shared.api.schemas.base import APIResponse
from app.modules.assets.service.assets_service import AssetsService
from app.modules.assets.schemas import (
    CreateComponentRequest,
    UpdateComponentRequest,
    ComponentResponse,
    CreateDutRequest,
    UpdateDutRequest,
    DutResponse,
    CreateTestPlanComponentRequest,
    TestPlanComponentResponse,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


def get_assets_service() -> AssetsService:
    return AssetsService()


AssetsServiceDep = Annotated[AssetsService, Depends(get_assets_service)]


# ==================== Component Library ====================

@router.post(
    "/components",
    response_model=APIResponse[ComponentResponse],
    status_code=201,
    summary="创建部件字典项",
)
async def create_component(
    request: CreateComponentRequest,
    service: AssetsServiceDep,
):
    try:
        data = await service.create_component(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/components/{part_number}",
    response_model=APIResponse[ComponentResponse],
    summary="获取部件详情",
)
async def get_component(
    part_number: str,
    service: AssetsServiceDep,
):
    try:
        data = await service.get_component(part_number)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="component not found")


@router.get(
    "/components",
    response_model=APIResponse[List[ComponentResponse]],
    summary="查询部件列表",
)
async def list_components(
    service: AssetsServiceDep,
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    lifecycle_status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await service.list_components(
        category=category,
        subcategory=subcategory,
        vendor=vendor,
        model=model,
        lifecycle_status=lifecycle_status,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.put(
    "/components/{part_number}",
    response_model=APIResponse[ComponentResponse],
    summary="更新部件信息",
)
async def update_component(
    part_number: str,
    request: UpdateComponentRequest,
    service: AssetsServiceDep,
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_component(part_number, payload)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="component not found")


@router.delete(
    "/components/{part_number}",
    response_model=APIResponse[dict],
    summary="删除部件",
)
async def delete_component(
    part_number: str,
    service: AssetsServiceDep,
):
    try:
        await service.delete_component(part_number)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="component not found")


# ==================== DUT ====================

@router.post(
    "/duts",
    response_model=APIResponse[DutResponse],
    status_code=201,
    summary="创建设备资产",
)
async def create_dut(
    request: CreateDutRequest,
    service: AssetsServiceDep,
):
    try:
        data = await service.create_dut(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/duts/{asset_id}",
    response_model=APIResponse[DutResponse],
    summary="获取设备资产详情",
)
async def get_dut(
    asset_id: str,
    service: AssetsServiceDep,
):
    try:
        data = await service.get_dut(asset_id)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="dut not found")


@router.get(
    "/duts",
    response_model=APIResponse[List[DutResponse]],
    summary="查询设备资产列表",
)
async def list_duts(
    service: AssetsServiceDep,
    status: Optional[str] = Query(None),
    owner_team: Optional[str] = Query(None),
    rack_location: Optional[str] = Query(None),
    health_status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await service.list_duts(
        status=status,
        owner_team=owner_team,
        rack_location=rack_location,
        health_status=health_status,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.put(
    "/duts/{asset_id}",
    response_model=APIResponse[DutResponse],
    summary="更新设备资产",
)
async def update_dut(
    asset_id: str,
    request: UpdateDutRequest,
    service: AssetsServiceDep,
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        data = await service.update_dut(asset_id, payload)
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="dut not found")


@router.delete(
    "/duts/{asset_id}",
    response_model=APIResponse[dict],
    summary="删除设备资产",
)
async def delete_dut(
    asset_id: str,
    service: AssetsServiceDep,
):
    try:
        await service.delete_dut(asset_id)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="dut not found")


# ==================== Test Plan Component ====================

@router.post(
    "/plan-components",
    response_model=APIResponse[TestPlanComponentResponse],
    status_code=201,
    summary="创建测试计划关联部件",
)
async def create_plan_component(
    request: CreateTestPlanComponentRequest,
    service: AssetsServiceDep,
):
    try:
        data = await service.create_plan_component(request.model_dump())
        return APIResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/plan-components",
    response_model=APIResponse[List[TestPlanComponentResponse]],
    summary="查询测试计划关联部件",
)
async def list_plan_components(
    service: AssetsServiceDep,
    plan_id: Optional[str] = Query(None),
    part_number: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await service.list_plan_components(
        plan_id=plan_id,
        part_number=part_number,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=data)


@router.delete(
    "/plan-components",
    response_model=APIResponse[dict],
    summary="删除测试计划关联部件",
)
async def delete_plan_component(
    service: AssetsServiceDep,
    plan_id: str = Query(...),
    part_number: str = Query(...),
):
    try:
        await service.delete_plan_component(plan_id, part_number)
        return APIResponse(data={"deleted": True})
    except KeyError:
        raise HTTPException(status_code=404, detail="plan component not found")

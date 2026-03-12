"""硬件与资产管理路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission
from app.modules.assets.service.assets_service import AssetsService
from app.shared.infrastructure.resource_lock import get_lock_manager
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
    dependencies=[Depends(require_permission("assets:write"))],
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
    dependencies=[Depends(require_permission("assets:read"))],
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
    dependencies=[Depends(require_permission("assets:read"))],
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
    dependencies=[Depends(require_permission("assets:write"))],
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
    dependencies=[Depends(require_permission("assets:write"))],
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
    dependencies=[Depends(require_permission("assets:write"))],
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
    dependencies=[Depends(require_permission("assets:read"))],
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
    dependencies=[Depends(require_permission("assets:read"))],
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
    dependencies=[Depends(require_permission("assets:write"))],
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
    dependencies=[Depends(require_permission("assets:write"))],
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


@router.post(
    "/duts/{asset_id}/test-status",
    response_model=APIResponse[dict],
    summary="测试设备状态（OS + BMC）",
    dependencies=[Depends(require_permission("assets:read"))],
)
async def test_dut_status(
    asset_id: str,
    service: AssetsServiceDep,
    use_lock: bool = Query(True, description="是否使用资源锁"),
    lock_ttl: int = Query(300, ge=1, le=3600, description="锁超时时间（秒）"),
    wait_timeout: float = Query(0, ge=0, le=300, description="等待获取锁的超时时间（秒）"),
):
    """测试 DUT 设备状态，包括 OS 状态（SSH）和 BMC 状态（Redfish API）

    返回设备状态信息：
    - os_status: OS 连接状态
    - bmc_status: BMC 连接状态
    - overall_status: 整体状态（healthy/degraded/unreachable）
    - lock_acquired: 是否成功获取锁
    - lock_owner: 锁持有者标识

    参数说明：
    - use_lock: 是否使用资源锁防止并发测试冲突，默认为 True
    - lock_ttl: 锁超时时间（秒），默认 300 秒
    - wait_timeout: 等待获取锁的超时时间（秒），0 表示不等待，默认为 0
    """
    try:
        data = await service.test_dut_status(
            asset_id=asset_id,
            use_lock=use_lock,
            lock_ttl=lock_ttl,
            wait_timeout=wait_timeout
        )
        return APIResponse(data=data)
    except KeyError:
        raise HTTPException(status_code=404, detail="dut not found")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "/duts/{asset_id}/lock-status",
    response_model=APIResponse[dict],
    summary="获取设备锁状态",
    dependencies=[Depends(require_permission("assets:read"))],
)
async def get_dut_lock_status(
    asset_id: str,
):
    """获取 DUT 设备的锁状态信息

    返回：
    - is_locked: 是否被锁定
    - lock_info: 锁详细信息（如果被锁定）
    """
    lock_manager = get_lock_manager()
    is_locked = await lock_manager.is_locked(resource_id=asset_id, lock_type="dut_test")
    
    lock_info = None
    if is_locked:
        lock_info = await lock_manager.get_lock_info(resource_id=asset_id, lock_type="dut_test")
    
    return APIResponse(data={
        "asset_id": asset_id,
        "is_locked": is_locked,
        "lock_info": lock_info
    })


@router.delete(
    "/duts/{asset_id}/lock",
    response_model=APIResponse[dict],
    summary="强制释放设备锁",
    dependencies=[Depends(require_permission("assets:write"))],
)
async def force_release_dut_lock(
    asset_id: str,
):
    """强制释放 DUT 设备的锁（管理员操作）

    注意：此操作会强制释放锁，可能导致正在进行的测试任务中断。
    建议仅在锁异常未释放时使用。
    """
    lock_manager = get_lock_manager()
    released = await lock_manager.force_release_lock(resource_id=asset_id, lock_type="dut_test")
    
    return APIResponse(data={
        "asset_id": asset_id,
        "released": released,
        "message": "Lock released successfully" if released else "No lock found"
    })


# ==================== Test Plan Component ====================

@router.post(
    "/plan-components",
    response_model=APIResponse[TestPlanComponentResponse],
    status_code=201,
    summary="创建测试计划关联部件",
    dependencies=[Depends(require_permission("assets:write"))],
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
    dependencies=[Depends(require_permission("assets:read"))],
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
    dependencies=[Depends(require_permission("assets:write"))],
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

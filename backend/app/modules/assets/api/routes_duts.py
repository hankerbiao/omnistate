"""DUT 测试机 API 路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.assets.api.dependencies import DutServiceDep
from app.modules.assets.schemas.dut import (
    CreateDutRequest,
    DutDetailResponse,
    DutResponse,
    SyncTmmsRequest,
    SyncTmmsResponse,
    UpdateDutRequest,
)
from app.modules.assets.service.dut_service import DutAlreadyExistsError, DutNotFoundError
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/duts", tags=["DUTs"])


@router.post(
    "",
    response_model=APIResponse[DutResponse],
    status_code=201,
    summary="创建 DUT",
    dependencies=[Depends(require_permission("duts:write"))],
)
async def create_dut(
    request: CreateDutRequest,
    service: DutServiceDep,
    current_user: dict = Depends(get_current_user),
):
    """创建新的 DUT 测试机"""
    try:
        data = request.model_dump()
        data["created_by"] = current_user.get("user_id")
        result = await service.create_dut(data)
        # 返回时不包含密码
        return APIResponse(data=_mask_passwords(result))
    except DutAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get(
    "",
    response_model=APIResponse[List[DutResponse]],
    summary="查询 DUT 列表",
    dependencies=[Depends(require_permission("duts:read"))],
)
async def list_duts(
    service: DutServiceDep,
    status: Optional[str] = Query(None, description="按状态筛选"),
    region: Optional[str] = Query(None, description="按区域筛选"),
    search: Optional[str] = Query(None, description="搜索名称/IP"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询 DUT 测试机列表"""
    duts, total = await service.list_duts(
        status=status,
        region=region,
        search=search,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=[_mask_passwords(d) for d in duts], meta={"total": total})


@router.get(
    "/regions",
    response_model=APIResponse[List[str]],
    summary="获取区域列表",
    dependencies=[Depends(require_permission("duts:read"))],
)
async def get_regions(service: DutServiceDep):
    """获取所有区域列表"""
    regions = await service.get_dut_regions()
    return APIResponse(data=regions)


@router.get(
    "/{dut_id}",
    response_model=APIResponse[DutDetailResponse],
    summary="获取 DUT 详情",
    dependencies=[Depends(require_permission("duts:read"))],
)
async def get_dut(
    dut_id: str,
    service: DutServiceDep,
):
    """获取 DUT 测试机详情（包含密码）"""
    try:
        result = await service.get_dut(dut_id)
        return APIResponse(data=result)
    except DutNotFoundError:
        raise HTTPException(status_code=404, detail="DUT not found")


@router.put(
    "/{dut_id}",
    response_model=APIResponse[DutResponse],
    summary="更新 DUT",
    dependencies=[Depends(require_permission("duts:write"))],
)
async def update_dut(
    dut_id: str,
    request: UpdateDutRequest,
    service: DutServiceDep,
    current_user: dict = Depends(get_current_user),
):
    """更新 DUT 测试机信息"""
    try:
        data = request.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="no fields to update")
        data["updated_by"] = current_user.get("user_id")
        result = await service.update_dut(dut_id, data)
        return APIResponse(data=_mask_passwords(result))
    except DutNotFoundError:
        raise HTTPException(status_code=404, detail="DUT not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{dut_id}",
    response_model=APIResponse[dict],
    summary="删除 DUT",
    dependencies=[Depends(require_permission("duts:write"))],
)
async def delete_dut(
    dut_id: str,
    service: DutServiceDep,
):
    """删除 DUT 测试机"""
    try:
        await service.delete_dut(dut_id)
        return APIResponse(data={"deleted": True, "dut_id": dut_id})
    except DutNotFoundError:
        raise HTTPException(status_code=404, detail="DUT not found")


@router.post(
    "/sync-tmms",
    response_model=APIResponse[SyncTmmsResponse],
    summary="从 TMMS 同步 DUT（预留）",
    dependencies=[Depends(require_permission("duts:write"))],
)
async def sync_from_tmms(
    request: SyncTmmsRequest,
    service: DutServiceDep,
):
    """从 TMMS 平台同步 DUT 测试机信息（预留接口）"""
    result = await service.sync_from_tmms(request)
    return APIResponse(data=result)


def _mask_passwords(dut: dict) -> dict:
    """屏蔽密码字段"""
    result = dut.copy()
    result.pop("bmc_password", None)
    result.pop("os_password", None)
    return result
"""DUT 测试机 API 路由"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.assets.api.dependencies import DutServiceDep
from app.modules.assets.schemas.dut import (
    CreateDutRequest,
    DutDetailResponse,
    DutResponse,
    ExternalMachineItem,
    ExternalMachinesResponse,
    ImportExternalMachinesRequest,
    ImportExternalMachinesResponse,
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


# ==================== 外部系统数据接口 ====================

FAKE_EXTERNAL_MACHINES: List[Dict[str, Any]] = [
    {
        "external_id": "TMMS-001",
        "name": "test-server-001",
        "bmc_ip": "192.168.1.101",
        "os_ip": "192.168.1.11",
        "region": "zone-a",
        "os_type": "Linux",
        "status": "available",
        "owner": "ops-team",
        "model": "Dell PowerEdge R750",
        "cpu": "Intel Xeon Gold 6338",
        "memory": "256GB DDR4",
        "storage": "2TB NVMe SSD",
        "tags": ["production", "critical"],
    },
    {
        "external_id": "TMMS-002",
        "name": "test-server-002",
        "bmc_ip": "192.168.1.102",
        "os_ip": "192.168.1.12",
        "region": "zone-a",
        "os_type": "Linux",
        "status": "available",
        "owner": "qa-team",
        "model": "Dell PowerEdge R740",
        "cpu": "Intel Xeon Silver 4214",
        "memory": "128GB DDR4",
        "storage": "1TB NVMe SSD",
        "tags": ["staging", "qa"],
    },
    {
        "external_id": "TMMS-003",
        "name": "test-server-003",
        "bmc_ip": "192.168.1.103",
        "os_ip": "192.168.1.13",
        "region": "zone-b",
        "os_type": "Linux",
        "status": "available",
        "owner": "dev-team",
        "model": "HP ProLiant DL380 Gen10",
        "cpu": "AMD EPYC 7543",
        "memory": "256GB DDR4",
        "storage": "4TB NVMe SSD",
        "tags": ["development", "flexible"],
    },
    {
        "external_id": "TMMS-004",
        "name": "test-server-004",
        "bmc_ip": "192.168.1.104",
        "os_ip": "192.168.1.14",
        "region": "zone-b",
        "os_type": "Windows",
        "status": "in_use",
        "owner": "qa-team",
        "model": "Dell PowerEdge R650",
        "cpu": "Intel Xeon Gold 5318Y",
        "memory": "128GB DDR4",
        "storage": "512GB NVMe SSD",
        "tags": ["windows-testing"],
    },
    {
        "external_id": "TMMS-005",
        "name": "test-server-005",
        "bmc_ip": "192.168.1.105",
        "os_ip": "192.168.1.15",
        "region": "zone-c",
        "os_type": "Linux",
        "status": "maintenance",
        "owner": "ops-team",
        "model": "Lenovo ThinkSystem SR650 V2",
        "cpu": "Intel Xeon Gold 6330",
        "memory": "512GB DDR4",
        "storage": "8TB NVMe SSD",
        "tags": ["performance-testing", "high-memory"],
    },
    {
        "external_id": "TMMS-006",
        "name": "test-server-006",
        "bmc_ip": "192.168.1.106",
        "os_ip": "192.168.1.16",
        "region": "zone-c",
        "os_type": "Linux",
        "status": "available",
        "owner": "dev-team",
        "model": "ASUS ESC4000A-E10",
        "cpu": "AMD EPYC 7713",
        "memory": "512GB DDR4",
        "storage": "2x4TB NVMe SSD",
        "tags": ["gpu-testing", "ai"],
    },
    {
        "external_id": "TMMS-007",
        "name": "test-server-007",
        "bmc_ip": "192.168.1.107",
        "os_ip": "192.168.1.17",
        "region": "zone-a",
        "os_type": "Linux",
        "status": "available",
        "owner": "qa-team",
        "model": "Dell PowerEdge R750xs",
        "cpu": "Intel Xeon Silver 4314",
        "memory": "64GB DDR4",
        "storage": "256GB SSD",
        "tags": ["light-testing"],
    },
    {
        "external_id": "TMMS-008",
        "name": "test-server-008",
        "bmc_ip": "192.168.1.108",
        "os_ip": "192.168.1.18",
        "region": "zone-b",
        "os_type": "Other",
        "status": "retired",
        "owner": "archive",
        "model": "HPE ProLiant ML350 Gen10",
        "cpu": "Intel Xeon Bronze 3204",
        "memory": "32GB DDR4",
        "storage": "500GB HDD",
        "tags": ["archived"],
    },
]


@router.get(
    "/external-machines",
    response_model=APIResponse[ExternalMachinesResponse],
    summary="获取外部系统机器列表（测试用 Fake API）",
    dependencies=[Depends(require_permission("duts:read"))],
)
async def get_external_machines(
    region: Optional[str] = Query(None, description="按区域筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    search: Optional[str] = Query(None, description="搜索名称/IP/型号"),
):
    """返回模拟的外部系统机器数据，用于测试同步功能"""
    machines = FAKE_EXTERNAL_MACHINES

    # 应用筛选
    if region:
        machines = [m for m in machines if m.get("region") == region]
    if status:
        machines = [m for m in machines if m.get("status") == status.lower()]
    if search:
        keyword = search.lower()
        machines = [
            m
            for m in machines
            if keyword in m.get("name", "").lower()
            or keyword in m.get("bmc_ip", "").lower()
            or keyword in m.get("os_ip", "").lower()
            or keyword in m.get("model", "").lower()
        ]

    # 获取所有区域
    all_regions = sorted(set(m.get("region") for m in FAKE_EXTERNAL_MACHINES))

    response = ExternalMachinesResponse(
        items=[ExternalMachineItem(**m) for m in machines],
        total=len(machines),
        regions=all_regions,
    )
    return APIResponse(data=response)


@router.post(
    "/import-external-machines",
    response_model=APIResponse[ImportExternalMachinesResponse],
    summary="导入选定的外部系统机器",
    dependencies=[Depends(require_permission("duts:write"))],
)
async def import_external_machines(
    request: ImportExternalMachinesRequest,
    service: DutServiceDep,
    current_user: dict = Depends(get_current_user),
):
    """将选定的外部系统机器批量导入到 DUT 列表"""
    result = await service.import_external_machines(
        external_items=request.items,
        created_by=current_user.get("user_id", "system"),
    )
    return APIResponse(data=result)


def _mask_passwords(dut: dict) -> dict:
    """屏蔽密码字段"""
    result = dut.copy()
    result.pop("bmc_password", None)
    result.pop("os_password", None)
    return result
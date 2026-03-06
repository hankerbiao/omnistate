"""测试需求 API 路由"""
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.modules.test_specs.service import RequirementService
from app.shared.core.logger import log as logger
from app.modules.test_specs.schemas import (
    CreateRequirementRequest,
    UpdateRequirementRequest,
    RequirementResponse,
)

router = APIRouter(prefix="/requirements", tags=["Requirements"])


def get_requirement_service() -> RequirementService:
    """FastAPI 依赖：为每次请求提供服务实例。"""
    return RequirementService()


RequirementServiceDep = Annotated[RequirementService, Depends(get_requirement_service)]


@router.post(
    "",
    response_model=APIResponse[RequirementResponse],
    status_code=201,
    summary="创建测试需求",
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def create_requirement(
    request: CreateRequirementRequest,
    service: RequirementServiceDep,
    current_user=Depends(get_current_user),
):
    """创建需求。

    重要说明：
    - 权限由路由依赖 `requirements:write` 统一控制。
    - req_id 字段必须由后端自动生成，前端不应提供此字段。
    - 即使前端传递了 req_id，服务层也会忽略并重新生成。
    - `request.model_dump()` 直接透传到 Service，避免字段重命名转换。
    """
    try:
        payload = request.model_dump()

        # ⚠️ 安全检查：确保前端没有尝试提供 req_id
        if payload.get("req_id"):
            logger.warning(
                f"前端尝试传递 req_id={payload['req_id']}，将忽略并重新生成"
            )

        owner_id = str(payload.get("tpm_owner_id") or "").strip()
        if not owner_id:
            payload["tpm_owner_id"] = current_user["user_id"]
        data = await service.create_requirement(payload)
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
    service: RequirementServiceDep,
):
    """按业务主键 req_id 查询单条需求。"""
    try:
        data = await service.get_requirement(req_id)
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
    service: RequirementServiceDep,
    status: Optional[str] = Query(None),
    tpm_owner_id: Optional[str] = Query(None),
    manual_dev_id: Optional[str] = Query(None),
    auto_dev_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """分页查询需求，支持按状态/负责人过滤。"""
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
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def update_requirement(
    req_id: str,
    request: UpdateRequirementRequest,
    service: RequirementServiceDep,
):
    """更新需求（仅更新请求中显式提交字段）。"""
    try:
        # 仅保留调用方显式传入字段，避免把默认 None 覆盖到数据库。
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
    dependencies=[Depends(require_permission("requirements:write"))],
)
async def delete_requirement(
    req_id: str,
    service: RequirementServiceDep,
):
    """删除需求（服务层执行逻辑删除与关联校验）。"""
    try:
        await service.delete_requirement(req_id)
        return APIResponse(data={"deleted": True})
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="requirement not found")

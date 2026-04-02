from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.auth.api.dependencies import RbacServiceDep
from app.modules.auth.schemas import (
    CreatePermissionRequest,
    PermissionResponse,
    UpdatePermissionRequest,
)
from app.modules.auth.service import PermissionNotFoundError
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission

router = APIRouter()


@router.post(
    "/permissions",
    response_model=APIResponse[PermissionResponse],
    status_code=201,
    summary="创建权限",
)
async def create_permission(
    request: CreatePermissionRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:write")),
):
    try:
        return APIResponse(data=await service.create_permission(request.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get(
    "/permissions/{perm_id}",
    response_model=APIResponse[PermissionResponse],
    summary="获取权限详情",
)
async def get_permission(
    perm_id: str,
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:read")),
):
    try:
        return APIResponse(data=await service.get_permission(perm_id))
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")


@router.get(
    "/permissions",
    response_model=APIResponse[list[PermissionResponse]],
    summary="查询权限列表",
)
async def list_permissions(
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:read")),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return APIResponse(data=await service.list_permissions(limit=limit, offset=offset))


@router.put(
    "/permissions/{perm_id}",
    response_model=APIResponse[PermissionResponse],
    summary="更新权限",
)
async def update_permission(
    perm_id: str,
    request: UpdatePermissionRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("permissions:write")),
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        return APIResponse(data=await service.update_permission(perm_id, payload))
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.auth.api.dependencies import RbacServiceDep, require_admin_user
from app.modules.auth.schemas import (
    CreateRoleRequest,
    RoleResponse,
    UpdateRolePermissionsRequest,
    UpdateRoleRequest,
)
from app.modules.auth.service import PermissionNotFoundError, RoleNotFoundError
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission

router = APIRouter()


@router.post("/roles", response_model=APIResponse[RoleResponse], status_code=201, summary="创建角色")
async def create_role(
    request: CreateRoleRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:write")),
):
    try:
        return APIResponse(data=await service.create_role(request.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")


@router.get("/roles/{role_id}", response_model=APIResponse[RoleResponse], summary="获取角色详情")
async def get_role(
    role_id: str,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:read")),
):
    try:
        return APIResponse(data=await service.get_role(role_id))
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


@router.get("/roles", response_model=APIResponse[list[RoleResponse]], summary="查询角色列表")
async def list_roles(
    service: RbacServiceDep,
    _=Depends(require_permission("roles:read")),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return APIResponse(data=await service.list_roles(limit=limit, offset=offset))


@router.put("/roles/{role_id}", response_model=APIResponse[RoleResponse], summary="更新角色信息")
async def update_role(
    role_id: str,
    request: UpdateRoleRequest,
    service: RbacServiceDep,
    _=Depends(require_permission("roles:write")),
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        return APIResponse(data=await service.update_role(role_id, payload))
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


@router.patch(
    "/roles/{role_id}/permissions",
    response_model=APIResponse[RoleResponse],
    summary="更新角色权限",
)
async def update_role_permissions(
    role_id: str,
    request: UpdateRolePermissionsRequest,
    service: RbacServiceDep,
    _=Depends(require_admin_user),
):
    try:
        return APIResponse(data=await service.update_role_permissions(role_id, request.permission_ids))
    except PermissionNotFoundError:
        raise HTTPException(status_code=404, detail="permission not found")
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")

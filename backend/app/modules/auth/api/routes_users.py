from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.auth.api.dependencies import (
    NavigationAccessServiceDep,
    UserServiceDep,
    require_admin_user,
)
from app.modules.auth.schemas import (
    UpdateUserNavigationRequest,
    UpdateUserPasswordRequest,
    UpdateUserRequest,
    UpdateUserRolesRequest,
    UserNavigationResponse,
    UserResponse,
    CreateUserRequest,
)
from app.modules.auth.service import RoleNotFoundError, UserNotFoundError
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_any_permission, require_permission

router = APIRouter()


@router.post("/users", response_model=APIResponse[UserResponse], status_code=201, summary="创建用户")
async def create_user(
    request: CreateUserRequest,
    service: UserServiceDep,
    _=Depends(require_permission("users:write")),
):
    try:
        data = await service.create_user(request.model_dump())
        return APIResponse(data=data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")


@router.get("/users/{user_id}", response_model=APIResponse[UserResponse], summary="获取用户详情")
async def get_user(
    user_id: str,
    service: UserServiceDep,
    _=Depends(require_any_permission(["users:read", "work_items:read"])),
):
    try:
        return APIResponse(data=await service.get_user(user_id))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.get("/users", response_model=APIResponse[list[UserResponse]], summary="查询用户列表")
async def list_users(
    service: UserServiceDep,
    _=Depends(require_any_permission(["users:read", "work_items:read"])),
    status: Optional[str] = Query(None),
    role_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return APIResponse(data=await service.list_users(status=status, role_id=role_id, limit=limit, offset=offset))


@router.put("/users/{user_id}", response_model=APIResponse[UserResponse], summary="更新用户信息")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    service: UserServiceDep,
    _=Depends(require_permission("users:write")),
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="no fields to update")
        return APIResponse(data=await service.update_user(user_id, payload))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.patch("/users/{user_id}/roles", response_model=APIResponse[UserResponse], summary="更新用户角色")
async def update_user_roles(
    user_id: str,
    request: UpdateUserRolesRequest,
    service: UserServiceDep,
    _=Depends(require_admin_user),
):
    try:
        return APIResponse(data=await service.update_user_roles(user_id, request.role_ids))
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="role not found")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.patch("/users/{user_id}/password", response_model=APIResponse[UserResponse], summary="重置用户密码")
async def update_user_password(
    user_id: str,
    request: UpdateUserPasswordRequest,
    service: UserServiceDep,
    _=Depends(require_admin_user),
):
    try:
        return APIResponse(data=await service.update_user_password(user_id, request.new_password))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.get(
    "/admin/users/{user_id}/navigation",
    response_model=APIResponse[UserNavigationResponse],
    summary="获取用户导航访问权限（管理员）",
)
async def get_user_navigation(
    user_id: str,
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
):
    try:
        return APIResponse(data=UserNavigationResponse(**(await service.get_user_navigation(user_id))))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.put(
    "/admin/users/{user_id}/navigation",
    response_model=APIResponse[UserNavigationResponse],
    summary="更新用户导航访问权限（管理员）",
)
async def update_user_navigation(
    user_id: str,
    request: UpdateUserNavigationRequest,
    service: NavigationAccessServiceDep,
    _=Depends(require_admin_user),
):
    try:
        data = await service.update_user_navigation(user_id, request.allowed_nav_views)
        return APIResponse(data=UserNavigationResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

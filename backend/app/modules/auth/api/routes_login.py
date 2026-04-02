from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.api.dependencies import NavigationAccessServiceDep, UserServiceDep
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MePermissionsResponse,
    UserNavigationResponse,
    UserResponse,
)
from app.modules.auth.service import UserNotFoundError
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import create_access_token, get_current_user, require_permission

router = APIRouter()


@router.post("/login", response_model=APIResponse[LoginResponse], summary="用户登录")
async def login(request: LoginRequest, service: UserServiceDep):
    try:
        user = await service.authenticate_user(request.user_id, request.password)
        token = create_access_token(user["user_id"])
        return APIResponse(data=LoginResponse(access_token=token, user=UserResponse(**user)))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials")


@router.post(
    "/users/me/password",
    response_model=APIResponse[UserResponse],
    summary="用户自助修改密码",
)
async def change_my_password(
    request: ChangePasswordRequest,
    service: UserServiceDep,
    current_user=Depends(get_current_user),
):
    try:
        data = await service.change_password(
            current_user["user_id"],
            request.old_password,
            request.new_password,
        )
        return APIResponse(data=data)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid credentials")


@router.get(
    "/users/me/permissions",
    response_model=APIResponse[MePermissionsResponse],
    summary="获取当前用户权限",
)
async def get_my_permissions(service: UserServiceDep, current_user=Depends(get_current_user)):
    try:
        data = await service.get_effective_permissions(current_user["user_id"])
        return APIResponse(data=MePermissionsResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")


@router.get(
    "/users/me/navigation",
    response_model=APIResponse[UserNavigationResponse],
    summary="获取当前用户导航访问权限",
)
async def get_my_navigation(
    service: NavigationAccessServiceDep,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("navigation:read")),
):
    try:
        data = await service.get_user_navigation(current_user["user_id"])
        return APIResponse(data=UserNavigationResponse(**data))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from app.modules.auth.service import (
    NavigationAccessService,
    PermissionService,
    RoleService,
    UserService,
)
from app.shared.auth import get_current_user


def get_user_service() -> UserService:
    return UserService()


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_role_service() -> RoleService:
    return RoleService()


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]


def get_permission_service() -> PermissionService:
    return PermissionService()


PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]


def get_navigation_access_service() -> NavigationAccessService:
    return NavigationAccessService()


NavigationAccessServiceDep = Annotated[
    NavigationAccessService,
    Depends(get_navigation_access_service),
]


def is_admin_user(current_user: dict) -> bool:
    role_ids = current_user.get("role_ids", [])
    return any("ADMIN" in str(role_id).upper() for role_id in role_ids)


async def require_admin_user(current_user=Depends(get_current_user)):
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="admin only")
    return current_user

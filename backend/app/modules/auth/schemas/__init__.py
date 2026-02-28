"""RBAC API 模型汇总

AI 友好注释说明：
- 通过集中导出，便于 API 与 Service 引用。
- 该文件不包含业务逻辑，仅做模块化组织。
"""
from .rbac import (
    CreateUserRequest,
    UpdateUserRequest,
    UpdateUserRolesRequest,
    UpdateUserPasswordRequest,
    ChangePasswordRequest,
    LoginRequest,
    UserResponse,
    LoginResponse,
    MePermissionsResponse,
    NavigationPageResponse,
    UserNavigationResponse,
    UpdateUserNavigationRequest,
    CreateRoleRequest,
    UpdateRoleRequest,
    UpdateRolePermissionsRequest,
    RoleResponse,
    CreatePermissionRequest,
    UpdatePermissionRequest,
    PermissionResponse,
)

__all__ = [
    "CreateUserRequest",
    "UpdateUserRequest",
    "UpdateUserRolesRequest",
    "UpdateUserPasswordRequest",
    "ChangePasswordRequest",
    "LoginRequest",
    "UserResponse",
    "LoginResponse",
    "MePermissionsResponse",
    "NavigationPageResponse",
    "UserNavigationResponse",
    "UpdateUserNavigationRequest",
    "CreateRoleRequest",
    "UpdateRoleRequest",
    "UpdateRolePermissionsRequest",
    "RoleResponse",
    "CreatePermissionRequest",
    "UpdatePermissionRequest",
    "PermissionResponse",
]

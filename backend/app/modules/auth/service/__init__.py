"""RBAC 服务模块

AI 友好注释说明：
- 这里导出 Service，供 API 层依赖注入。
- 后续如有多个服务，可在此统一聚合。
"""
from .rbac_service import RbacService
from .navigation_page_service import NavigationPageService
from .exceptions import (
    RbacError,
    UserNotFoundError,
    RoleNotFoundError,
    PermissionNotFoundError,
    NavigationPageNotFoundError,
)

__all__ = [
    "RbacService",
    "NavigationPageService",
    "RbacError",
    "UserNotFoundError",
    "RoleNotFoundError",
    "PermissionNotFoundError",
    "NavigationPageNotFoundError",
]

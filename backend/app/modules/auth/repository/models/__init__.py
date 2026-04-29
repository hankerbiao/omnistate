"""权限管理模型模块

AI 友好注释说明：
- 统一导出文档模型与响应模型，方便外部引用。
- 该文件仅做导出聚合，不包含业务逻辑。
"""
from .rbac import (
    UserDoc,
    RoleDoc,
    PermissionDoc,
    UserModel,
    RoleModel,
    PermissionModel,
)
from .navigation import NavigationPageDoc, NavigationPageModel

__all__ = [
    "UserDoc",
    "RoleDoc",
    "PermissionDoc",
    "NavigationPageDoc",
    "UserModel",
    "RoleModel",
    "PermissionModel",
    "NavigationPageModel",
    "DOCUMENT_MODELS",
]

DOCUMENT_MODELS = [
    UserDoc,
    RoleDoc,
    PermissionDoc,
    NavigationPageDoc,
]

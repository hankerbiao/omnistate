"""RBAC 领域异常定义。"""


class RbacError(Exception):
    """RBAC 领域异常基类。"""


class UserNotFoundError(RbacError):
    """用户不存在。"""


class RoleNotFoundError(RbacError):
    """角色不存在。"""


class PermissionNotFoundError(RbacError):
    """权限不存在。"""

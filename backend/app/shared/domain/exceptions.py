"""
共享应用级异常基类

全局异常处理器通过捕获这些基类实现统一的 HTTP status mapping。
各模块的领域异常应继承自 AppError。
"""


class AppError(Exception):
    """应用层基础异常，所有业务异常的基类。"""
    pass


class NotFoundError(AppError):
    """资源不存在（HTTP 404）。"""
    pass


class ConflictError(AppError):
    """资源冲突，如重复创建等（HTTP 409）。"""
    pass


class ValidationError(AppError):
    """输入校验失败（HTTP 400）。"""
    pass


class PermissionDeniedError(AppError):
    """权限不足（HTTP 403）。"""
    pass

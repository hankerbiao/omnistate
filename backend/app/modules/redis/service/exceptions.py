"""Redis 模块异常定义。"""

from app.shared.domain.exceptions import AppError


class RedisConnectionError(AppError):
    """Redis 连接失败。"""

    def __init__(self, message: str = "Redis 连接失败"):
        super().__init__(message)


class RedisOperationError(AppError):
    """Redis 操作执行失败。"""

    def __init__(self, message: str = "Redis 操作失败"):
        super().__init__(message)

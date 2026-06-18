"""项目模块领域异常。"""

from __future__ import annotations

from app.shared.domain.exceptions import ConflictError, NotFoundError, ValidationError


class ProjectNotFoundError(NotFoundError):
    """项目不存在。"""
    pass


class ProjectKeyConflictError(ConflictError):
    """项目标识冲突。"""

    def __init__(self, key: str) -> None:
        super().__init__(f"项目标识已存在: {key}")
        self.key = key


class ProjectQueryError(ValidationError):
    """项目查询/操作参数错误。"""
    pass

"""项目模块领域异常。"""

from __future__ import annotations


class ProjectError(Exception):
    """项目模块基础异常。"""
    pass


class ProjectNotFoundError(ProjectError):
    """项目不存在。"""
    pass


class ProjectKeyConflictError(ProjectError):
    """项目标识冲突。"""
    def __init__(self, key: str) -> None:
        super().__init__(f"项目标识已存在: {key}")
        self.key = key


class ProjectQueryError(ProjectError):
    """项目查询/操作参数错误。"""
    pass

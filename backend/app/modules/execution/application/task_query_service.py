"""执行任务查询应用服务。"""

from __future__ import annotations

from app.modules.execution.application.task_query_mixin import ExecutionTaskQueryMixin


class ExecutionTaskQueryService(ExecutionTaskQueryMixin):
    """任务查询与序列化能力。"""

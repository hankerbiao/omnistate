"""执行代理应用服务。"""

from __future__ import annotations

from app.modules.execution.application.agent_mixin import ExecutionAgentMixin


class ExecutionAgentService(ExecutionAgentMixin):
    """执行代理注册、心跳和查询能力。"""

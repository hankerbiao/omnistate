"""执行任务应用服务兼容门面。"""

from __future__ import annotations

from typing import Any, Dict

from app.modules.execution.application.agent_service import ExecutionAgentService
from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.application.task_dispatch_service import ExecutionDispatchService
from app.modules.execution.application.task_query_service import ExecutionTaskQueryService
from app.modules.execution.schemas import DispatchTaskRequest, RerunTaskRequest
from app.shared.service import SequenceIdService


class ExecutionService:
    """兼容旧调用点，对外委托到更小的应用服务。"""

    def __init__(
        self,
        command_service: ExecutionTaskCommandService | None = None,
        query_service: ExecutionTaskQueryService | None = None,
        agent_service: ExecutionAgentService | None = None,
        dispatch_service: ExecutionDispatchService | None = None,
    ) -> None:
        self._dispatch_service = dispatch_service or ExecutionDispatchService()
        self._command_service = command_service or ExecutionTaskCommandService(
            dispatch_service=self._dispatch_service
        )
        self._query_service = query_service or ExecutionTaskQueryService()
        self._agent_service = agent_service or ExecutionAgentService()

    async def create_and_dispatch_task(
        self,
        request: DispatchTaskRequest,
        actor_id: str,
        sequence_service: SequenceIdService,
    ) -> Dict[str, Any]:
        return await self._command_service.create_and_dispatch_task(
            request=request,
            actor_id=actor_id,
            sequence_service=sequence_service,
        )

    async def delete_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        return await self._command_service.delete_task(task_id, actor_id=actor_id)

    async def dispatch_execution_task(
        self,
        command,
        actor_id: str,
    ) -> Dict[str, Any]:
        return await self._command_service.dispatch_execution_task(command, actor_id=actor_id)

    async def rerun_task(
        self,
        source_task_id: str,
        new_task_id: str,
        actor_id: str,
        request: RerunTaskRequest,
    ) -> Dict[str, Any]:
        return await self._command_service.rerun_task(
            source_task_id=source_task_id,
            new_task_id=new_task_id,
            actor_id=actor_id,
            request=request,
        )

    async def list_tasks(self):
        return await self._query_service.list_tasks()

    async def get_task_status(self, task_id: str):
        return await self._query_service.get_task_status(task_id)

    async def register_agent(self, payload):
        return await self._agent_service.register_agent(payload)

    async def heartbeat_agent(self, agent_id: str, payload):
        return await self._agent_service.heartbeat_agent(agent_id, payload)

    async def list_agents(self, region: str | None = None, status: str | None = None, online_only: bool = False):
        return await self._agent_service.list_agents(region=region, status=status, online_only=online_only)

    async def get_agent(self, agent_id: str):
        return await self._agent_service.get_agent(agent_id)

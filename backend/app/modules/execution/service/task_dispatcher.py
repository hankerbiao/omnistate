"""执行任务分发器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_helpers import build_dispatch_task_data
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.kafka import TaskMessage


@dataclass
class DispatchResult:
    """统一封装下发结果。"""

    success: bool
    channel: str
    message: str
    response: Dict[str, Any]
    error: str | None = None


class ExecutionTaskDispatcher:
    """任务分发器，通过 RabbitMQ 下发任务。"""

    async def dispatch(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        """通过 RabbitMQ 下发任务。"""
        return await self._dispatch_via_rabbitmq(command)

    async def _dispatch_via_rabbitmq(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        """通过 RabbitMQ 下发任务。"""
        from app.shared.infrastructure import get_rabbitmq_manager

        rabbitmq_manager = get_rabbitmq_manager()
        if not rabbitmq_manager:
            return DispatchResult(
                success=False,
                channel="RABBITMQ",
                message="RabbitMQ manager not available",
                response={"accepted": False, "message": "RabbitMQ manager not available"},
                error="RabbitMQ manager not available",
            )

        task_data = build_dispatch_task_data(command)
        task_message = TaskMessage(
            task_id=command.task_id,
            task_type="execution_task",
            task_data=task_data,
            source="dmlv4-execution-api",
            priority=1,
        )
        elog(
            "info",
            ExecutionNode.TASK_DISPATCH,
            "dispatching execution task via RabbitMQ",
            channel="RABBITMQ",
            queue="dmlv4.tasks",
        )
        elog(
            "debug",
            ExecutionNode.TASK_DISPATCH,
            "RabbitMQ execution dispatch payload",
            payload=task_data,
        )
        success = await rabbitmq_manager.send_task_async(task_message)
        if success:
            elog(
                "info",
                ExecutionNode.TASK_DISPATCH,
                "RabbitMQ execution dispatch accepted",
                outcome="success",
                channel="RABBITMQ",
            )
            return DispatchResult(
                success=True,
                channel="RABBITMQ",
                message="Task dispatched to RabbitMQ successfully",
                response={"accepted": True, "message": "Task dispatched to RabbitMQ successfully"},
            )

        elog(
            "warning",
            ExecutionNode.TASK_DISPATCH,
            "RabbitMQ execution dispatch rejected",
            outcome="failed",
            channel="RABBITMQ",
        )
        return DispatchResult(
            success=False,
            channel="RABBITMQ",
            message="Failed to dispatch task to RabbitMQ",
            response={"accepted": False, "message": "Failed to dispatch task to RabbitMQ"},
            error="Failed to send task to RabbitMQ",
        )

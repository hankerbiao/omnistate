"""执行任务分发器。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.shared.core.logger import log as logger
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
    """通过 RabbitMQ 分发任务。"""

    async def dispatch(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        # 固定使用 RabbitMQ 下发
        return await asyncio.to_thread(self._dispatch_via_rabbitmq, command)

    def _dispatch_via_rabbitmq(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
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

        task_message = TaskMessage(
            task_id=command.task_id,
            task_type="execution_task",
            task_data=command.dispatch_task_data,
            source="dmlv4-execution-api",
            priority=1,
        )
        logger.info(
            "Dispatching execution task via RabbitMQ: "
            f"task_id={command.task_id}, queue=dmlv4.tasks, agent_id={command.agent_id}"
        )
        logger.debug(
            "RabbitMQ execution dispatch payload: "
            f"task_id={command.task_id}, payload={command.dispatch_task_data}"
        )
        success = rabbitmq_manager.send_task(task_message)
        if success:
            logger.info(
                "RabbitMQ execution dispatch accepted: "
                f"task_id={command.task_id}, agent_id={command.agent_id}"
            )
            return DispatchResult(
                success=True,
                channel="RABBITMQ",
                message="Task dispatched to RabbitMQ successfully",
                response={"accepted": True, "message": "Task dispatched to RabbitMQ successfully"},
            )

        logger.warning(
            "RabbitMQ execution dispatch rejected: "
            f"task_id={command.task_id}, agent_id={command.agent_id}"
        )
        return DispatchResult(
            success=False,
            channel="RABBITMQ",
            message="Failed to dispatch task to RabbitMQ",
            response={"accepted": False, "message": "Failed to dispatch task to RabbitMQ"},
            error="Failed to send task to RabbitMQ",
        )

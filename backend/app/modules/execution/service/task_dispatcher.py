"""执行任务分发器。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_helpers import build_dispatch_task_data
from app.modules.execution.shared.execution_context import execution_scope
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.context import trace_scope
from app.shared.http import get_http_dispatch_client
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
    """任务分发器，支持 RabbitMQ 和 HTTP 两种渠道。"""

    async def dispatch(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        """根据配置选择下发渠道。"""
        from app.shared.config import get_settings

        settings = get_settings()
        mode = settings.execution.dispatch_mode.lower()

        if mode == "http":
            return await self._dispatch_via_http(command)
        return await self._dispatch_via_rabbitmq(command)

    def _dispatch_via_rabbitmq(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
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
        success = rabbitmq_manager.send_task(task_message)
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

    async def _dispatch_via_http(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        """通过 HTTP 下发任务（异步 fire-and-forget）。"""
        from app.shared.config import get_settings

        settings = get_settings()
        http_cfg = settings.execution.http_dispatch

        if not http_cfg.enabled:
            return DispatchResult(
                success=False,
                channel="HTTP",
                message="HTTP dispatch is disabled",
                response={"accepted": False, "message": "HTTP dispatch is disabled"},
                error="HTTP dispatch is disabled in configuration",
            )

        if not http_cfg.target_url:
            return DispatchResult(
                success=False,
                channel="HTTP",
                message="HTTP target_url is not configured",
                response={"accepted": False, "message": "HTTP target_url is not configured"},
                error="HTTP target_url is empty in configuration",
            )

        path = settings.execution.agent_dispatch_path
        full_url = f"{http_cfg.target_url.rstrip('/')}/{path.lstrip('/')}"

        task_data = build_dispatch_task_data(command)
        task_id = command.task_id
        agent_id = command.agent_id

        elog(
            "info",
            ExecutionNode.TASK_DISPATCH,
            "starting async HTTP dispatch",
            channel="HTTP",
            url=full_url,
            timeout_sec=http_cfg.timeout_sec,
        )
        elog(
            "debug",
            ExecutionNode.TASK_DISPATCH,
            "HTTP dispatch payload",
            payload=task_data,
        )

        asyncio.create_task(
            self._http_dispatch_background(
                full_url=full_url,
                task_data=task_data,
                task_id=task_id,
                agent_id=agent_id,
                timeout_sec=http_cfg.timeout_sec,
                headers=dict(http_cfg.headers),
                retry_times=http_cfg.retry_times,
            )
        )

        elog(
            "info",
            ExecutionNode.TASK_DISPATCH,
            "HTTP dispatch initiated",
            outcome="accepted",
            channel="HTTP",
        )
        return DispatchResult(
            success=True,
            channel="HTTP",
            message="Task dispatch initiated via HTTP (async)",
            response={"accepted": True, "message": "Task dispatch initiated via HTTP (async)"},
        )

    async def _http_dispatch_background(
        self,
        full_url: str,
        task_data: Dict[str, Any],
        task_id: str,
        agent_id: str | None,
        timeout_sec: int,
        headers: Dict[str, str],
        retry_times: int,
    ) -> None:
        """后台执行 HTTP 请求（不阻塞主流程）。"""
        async with trace_scope(request_id=f"http-dispatch:{task_id}"):
            async with execution_scope(
                task_id=task_id,
                agent_id=agent_id or "-",
                node=ExecutionNode.HTTP_DISPATCH_BG.value,
            ):
                try:
                    http_client = get_http_dispatch_client()
                    success, response_data, error = await http_client.post_json(
                        url=full_url,
                        data=task_data["data"],
                        timeout_sec=timeout_sec,
                        headers=headers,
                        retry_times=retry_times,
                    )

                    if success:
                        elog(
                            "info",
                            ExecutionNode.HTTP_DISPATCH_BG,
                            "HTTP background dispatch success",
                            outcome="success",
                            response_keys=list(response_data.keys()) if response_data else [],
                        )
                    else:
                        elog(
                            "warning",
                            ExecutionNode.HTTP_DISPATCH_BG,
                            "HTTP background dispatch failed",
                            outcome="failed",
                            error=error,
                        )

                except Exception as exc:
                    elog(
                        "error",
                        ExecutionNode.HTTP_DISPATCH_BG,
                        "HTTP background dispatch exception",
                        outcome="failed",
                        error=str(exc),
                    )

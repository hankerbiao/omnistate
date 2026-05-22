"""执行任务分发器。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.task_command_helpers import build_dispatch_task_data
from app.shared.core.logger import log as logger
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
        else:
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
        logger.info(
            "Dispatching execution task via RabbitMQ: "
            f"task_id={command.task_id}, queue=dmlv4.tasks, agent_id={command.agent_id}"
        )
        logger.debug(
            "RabbitMQ execution dispatch payload: "
            f"task_id={command.task_id}, payload={task_data}"
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

        # 构造完整 URL
        path = settings.execution.agent_dispatch_path
        full_url = f"{http_cfg.target_url.rstrip('/')}/{path.lstrip('/')}"

        task_data = build_dispatch_task_data(command)
        task_id = command.task_id
        agent_id = command.agent_id

        logger.info(
            f"[HTTP DISPATCH] Starting async HTTP dispatch (fire-and-forget):\n"
            f"  task_id={task_id}\n"
            f"  url={full_url}\n"
            f"  agent_id={agent_id}\n"
            f"  timeout={http_cfg.timeout_sec}s"
        )
        logger.debug(
            f"[HTTP DISPATCH] Full payload:\n"
            f"  task_id={task_id}\n"
            f"  payload={task_data}"
        )

        # 异步 fire-and-forget: 创建后台任务执行 HTTP 请求
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

        # 立即返回成功，不等待 HTTP 响应
        logger.info(
            f"[HTTP DISPATCH] Dispatch initiated (async): task_id={task_id}, agent_id={agent_id}"
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
                logger.info(
                    f"[HTTP DISPATCH] Background dispatch success:\n"
                    f"  task_id={task_id}\n"
                    f"  agent_id={agent_id}\n"
                    f"  response_keys={list(response_data.keys()) if response_data else []}"
                )
            else:
                logger.warning(
                    f"[HTTP DISPATCH] Background dispatch failed:\n"
                    f"  task_id={task_id}\n"
                    f"  agent_id={agent_id}\n"
                    f"  error={error}"
                )

        except Exception as e:
            logger.error(
                f"[HTTP DISPATCH] Background dispatch exception:\n"
                f"  task_id={task_id}\n"
                f"  agent_id={agent_id}\n"
                f"  error={e}"
            )
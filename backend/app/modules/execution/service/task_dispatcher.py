"""执行任务分发器。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

import requests

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import ExecutionAgentDoc
from app.shared.core.logger import log as logger
from app.shared.db.config import settings
from app.shared.kafka import TaskMessage


@dataclass
class DispatchResult:
    """统一封装不同通道的下发结果。"""

    success: bool
    channel: str
    message: str
    response: Dict[str, Any]
    error: str | None = None


class ExecutionTaskDispatcher:
    """根据配置选择 Kafka 或 HTTP 分发任务。"""

    async def dispatch(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        mode = command.dispatch_channel.strip().lower()
        if mode == "http":
            return await self._dispatch_via_http(command)
        return self._dispatch_via_kafka(command)

    def _dispatch_via_kafka(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        from app.shared.infrastructure import get_kafka_manager

        kafka_manager = get_kafka_manager()
        if not kafka_manager:
            return DispatchResult(
                success=False,
                channel="KAFKA",
                message="Kafka manager not available",
                response={"accepted": False, "message": "Kafka manager not available"},
                error="Kafka manager not available",
            )

        task_message = TaskMessage(
            task_id=command.task_id,
            task_type="execution_task",
            task_data=command.kafka_task_data,
            source="dmlv4-execution-api",
            priority=1,
        )
        logger.info(
            "Dispatching execution task via Kafka: "
            f"task_id={command.task_id}, topic=default-task-topic, agent_id={command.agent_id}"
        )
        logger.debug(
            "Kafka execution dispatch payload: "
            f"task_id={command.task_id}, payload={command.kafka_task_data}"
        )
        success = kafka_manager.send_task(task_message)
        if success:
            logger.info(
                "Kafka execution dispatch accepted: "
                f"task_id={command.task_id}, agent_id={command.agent_id}"
            )
            return DispatchResult(
                success=True,
                channel="KAFKA",
                message="Task dispatched to Kafka successfully",
                response={"accepted": True, "message": "Task dispatched to Kafka successfully"},
            )
        logger.warning(
            "Kafka execution dispatch rejected: "
            f"task_id={command.task_id}, agent_id={command.agent_id}"
        )
        return DispatchResult(
            success=False,
            channel="KAFKA",
            message="Failed to dispatch task to Kafka",
            response={"accepted": False, "message": "Failed to dispatch task to Kafka"},
            error="Failed to send task to Kafka",
        )

    async def _dispatch_via_http(self, command: DispatchExecutionTaskCommand) -> DispatchResult:
        if not command.agent_id:
            return DispatchResult(
                success=False,
                channel="HTTP",
                message="agent_id is required for HTTP dispatch mode",
                response={"accepted": False, "message": "agent_id is required for HTTP dispatch mode"},
                error="agent_id is required for HTTP dispatch mode",
            )

        agent_doc = await ExecutionAgentDoc.find_one({
            "agent_id": command.agent_id,
            "is_deleted": False,
        })
        if not agent_doc:
            return DispatchResult(
                success=False,
                channel="HTTP",
                message=f"Execution agent not found: {command.agent_id}",
                response={"accepted": False, "message": f"Execution agent not found: {command.agent_id}"},
                error=f"Execution agent not found: {command.agent_id}",
            )
        if agent_doc.status != "ONLINE":
            return DispatchResult(
                success=False,
                channel="HTTP",
                message=f"Execution agent is not online: {command.agent_id}",
                response={"accepted": False, "message": f"Execution agent is not online: {command.agent_id}"},
                error=f"Execution agent is not online: {command.agent_id}",
            )
        if not agent_doc.base_url:
            return DispatchResult(
                success=False,
                channel="HTTP",
                message=f"Execution agent base_url is empty: {command.agent_id}",
                response={
                    "accepted": False,
                    "message": f"Execution agent base_url is empty: {command.agent_id}",
                },
                error=f"Execution agent base_url is empty: {command.agent_id}",
            )

        url = f"{agent_doc.base_url.rstrip('/')}{settings.EXECUTION_AGENT_DISPATCH_PATH}"
        logger.info(
            "Dispatching execution task via HTTP: "
            f"task_id={command.task_id}, agent_id={agent_doc.agent_id}, hostname={agent_doc.hostname}, "
            f"ip={agent_doc.ip}, port={agent_doc.port}, region={agent_doc.region}, "
            f"base_url={agent_doc.base_url}"
        )
        logger.debug(
            "HTTP execution dispatch payload: "
            f"task_id={command.task_id}, target_url={url}, payload={command.kafka_task_data}"
        )
        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=command.kafka_task_data,
                timeout=settings.EXECUTION_HTTP_TIMEOUT_SEC,
            )
            accepted = response.status_code in {200, 201, 202}
            payload = self._build_http_response_payload(response, accepted)
            logger.info(
                "HTTP execution dispatch completed: "
                f"task_id={command.task_id}, agent_id={agent_doc.agent_id}, "
                f"status_code={response.status_code}, accepted={accepted}"
            )
            logger.debug(
                "HTTP execution dispatch response: "
                f"task_id={command.task_id}, agent_id={agent_doc.agent_id}, response={payload}"
            )
            return DispatchResult(
                success=accepted,
                channel="HTTP",
                message=payload["message"],
                response=payload,
                error=None if accepted else payload["message"],
            )
        except requests.RequestException as exc:
            logger.warning(f"HTTP dispatch failed for task {command.task_id}: {exc}")
            return DispatchResult(
                success=False,
                channel="HTTP",
                message=f"HTTP dispatch failed: {exc}",
                response={"accepted": False, "message": f"HTTP dispatch failed: {exc}"},
                error=f"HTTP dispatch failed: {exc}",
            )

    @staticmethod
    def _build_http_response_payload(response: requests.Response, accepted: bool) -> Dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}
        return {
            "accepted": accepted,
            "message": (
                "Task dispatched via HTTP successfully"
                if accepted else f"HTTP dispatch failed with status {response.status_code}"
            ),
            "status_code": response.status_code,
            "body": body,
        }

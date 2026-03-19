"""Kafka handlers for the execution module."""

from __future__ import annotations

from typing import Any

from app.modules.execution.schemas.kafka_events import ExecutionResultEvent
from app.shared.core.logger import log as logger
from app.shared.kafka import KafkaTopicHandlerRegistry, load_kafka_config


class ExecutionKafkaHandlers:
    """Execution module Kafka handlers."""

    async def handle_result_event(
        self,
        event: ExecutionResultEvent,
        metadata: dict[str, Any],
    ) -> None:
        logger.info(
            "Received execution result event: "
            f"task_id={event.task_id}, status={event.status}, offset={metadata.get('offset')}"
        )


def register_execution_kafka_handlers(
    registry: KafkaTopicHandlerRegistry,
) -> KafkaTopicHandlerRegistry:
    config = load_kafka_config()
    handlers = ExecutionKafkaHandlers()
    registry.register(
        topic=config.result_topic,
        schema=ExecutionResultEvent,
        handler=handlers.handle_result_event,
    )
    return registry

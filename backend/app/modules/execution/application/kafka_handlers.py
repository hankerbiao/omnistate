"""Kafka handlers for the execution module."""

from __future__ import annotations

from typing import Any

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService
from app.modules.execution.schemas.kafka_events import ExecutionResultEvent, TestEvent
from app.shared.core.logger import log as logger
from app.shared.kafka import KafkaTopicHandlerRegistry, load_kafka_config


class ExecutionKafkaHandlers:
    """Execution module Kafka handlers."""

    def __init__(self) -> None:
        self._event_ingest_service = ExecutionEventIngestService()

    async def handle_result_event(
        self,
        event: ExecutionResultEvent,
        metadata: dict[str, Any],
    ) -> None:
        logger.info(
            "Received execution result event: "
            f"task_id={event.task_id}, status={event.status}, offset={metadata.get('offset')}"
        )

    async def handle_test_event(
        self,
        event: TestEvent,
        metadata: dict[str, Any],
    ) -> None:
        topic = str(metadata.get("topic") or "test-events")
        logger.debug(
            "Received execution test event: "
            f"topic={topic}, task_id={event.task_id}, case_id={event.case_id}, "
            f"event_id={event.event_id}, event_type={event.event_type}, "
            f"phase={event.phase}, offset={metadata.get('offset')}"
        )
        await self._event_ingest_service.ingest_event(
            topic=topic,
            event_payload=event.model_dump(mode="json", by_alias=True),
            metadata=metadata,
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
    registry.register(
        topic=config.test_events_topic,
        schema=TestEvent,
        handler=handlers.handle_test_event,
    )
    return registry

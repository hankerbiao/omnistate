"""Kafka handlers for the execution module."""

from __future__ import annotations

from typing import Any

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService
from app.modules.execution.schemas.kafka_events import ExecutionResultEvent, RawTestEventEnvelope
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
        event: RawTestEventEnvelope,
        metadata: dict[str, Any],
    ) -> None:
        topic = str(metadata.get("topic") or "test-events")
        payload = dict(event.payload)
        schema_name = str(payload.get("schema") or "")
        if schema_name.endswith("-test-event@1"):
            await self._ingest_single_test_event(topic, payload, metadata)
            return
        if schema_name.endswith("-test-event-batch@1"):
            await self._ingest_test_event_batch(topic, payload, metadata)
            return
        raise ValueError(f"Unsupported test event schema: {schema_name}")

    async def _ingest_single_test_event(
        self,
        topic: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        logger.debug(
            "Received execution test event envelope: "
            f"topic={topic}, schema={payload.get('schema')}, offset={metadata.get('offset')}"
        )
        await self._event_ingest_service.ingest_event(
            topic=topic,
            event_payload=payload,
            metadata=metadata,
        )

    async def _ingest_test_event_batch(
        self,
        topic: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        schema_name = str(payload.get("schema") or "")
        event_schema_name = schema_name.replace("-batch@1", "@1")
        events = self._extract_batch_items(payload)
        logger.info(
            "Received execution test event batch: "
            f"topic={topic}, schema={schema_name}, batch_size={len(events)}, offset={metadata.get('offset')}"
        )
        for index, item in enumerate(events):
            event_payload = {
                **dict(item),
                "schema": dict(item).get("schema") or event_schema_name,
            }
            event_metadata = {**metadata, "batch_index": index, "batch_size": len(events)}
            await self._event_ingest_service.ingest_event(
                topic=topic,
                event_payload=event_payload,
                metadata=event_metadata,
            )

    @staticmethod
    def _extract_batch_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ("events", "tests", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, dict)]
        raise ValueError("test event batch payload must contain one of: events, tests, items, records")


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
        schema=RawTestEventEnvelope,
        handler=handlers.handle_test_event,
    )
    return registry

"""执行模块 Kafka 消费处理器。"""

from __future__ import annotations

from typing import Any

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService
from app.modules.execution.schemas.kafka_events import ExecutionResultEvent, RawTestEventEnvelope
from app.modules.execution.shared.execution_context import (
    bind_execution_context_from_payload,
    execution_scope,
)
from app.modules.execution.shared.execution_log import ExecutionNode, elog
from app.shared.kafka import KafkaTopicHandlerRegistry, load_kafka_config


class ExecutionKafkaHandlers:
    """执行模块 Kafka 消费处理器。

    当前执行域会消费两类 Kafka 消息：

    1. 结果消息 `ExecutionResultEvent`
       主要用于记录任务级结果回报，当前这里只做日志留痕。
    2. 测试事件消息 `RawTestEventEnvelope`
       这是平台真正驱动任务/用例当前态推进的核心输入，最终都会进入
       `ExecutionEventIngestService` 做统一入库和状态聚合。
    """

    def __init__(self) -> None:
        """初始化事件落库服务。

        这里不在 handler 内直接操作任务文档，而是统一委托给
        `ExecutionEventIngestService`，避免 Kafka 接入层和执行态聚合逻辑耦合。
        """
        self._event_ingest_service = ExecutionEventIngestService()

    async def handle_result_event(
        self,
        event: ExecutionResultEvent,
        metadata: dict[str, Any],
    ) -> None:
        """处理任务级结果消息。"""
        async with execution_scope(task_id=event.task_id, node=ExecutionNode.KAFKA_RESULT.value):
            elog(
                "info",
                ExecutionNode.KAFKA_RESULT,
                "received execution result event",
                outcome=event.status,
                offset=metadata.get("offset"),
                status=event.status,
            )

    async def handle_test_event(
        self,
        event: RawTestEventEnvelope,
        metadata: dict[str, Any],
    ) -> None:
        """处理测试事件总入口。"""
        topic = str(metadata.get("topic") or "test-events")
        payload = dict(event.payload)
        schema_name = str(payload.get("schema") or "")
        bind_execution_context_from_payload(payload)
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
        """消费单条测试事件并交给执行事件服务处理。"""
        task_id = str(payload.get("task_id") or "-")
        async with execution_scope(
            task_id=task_id,
            case_id=str(payload.get("case_id") or "-") if payload.get("case_id") else None,
            event_id=str(payload.get("event_id") or "-") if payload.get("event_id") else None,
            node=ExecutionNode.EVENT_INGEST.value,
        ):
            elog(
                "debug",
                ExecutionNode.EVENT_INGEST,
                "received execution test event envelope",
                topic=topic,
                schema=payload.get("schema"),
                offset=metadata.get("offset"),
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
        """消费批量测试事件，并拆分成多条单事件顺序处理。"""
        schema_name = str(payload.get("schema") or "")
        event_schema_name = schema_name.replace("-batch@1", "@1")
        events = self._extract_batch_items(payload)
        elog(
            "info",
            ExecutionNode.KAFKA_BATCH,
            "received execution test event batch",
            topic=topic,
            schema=schema_name,
            batch_size=len(events),
            offset=metadata.get("offset"),
        )
        for index, item in enumerate(events):
            event_payload = {
                **dict(item),
                "schema": dict(item).get("schema") or event_schema_name,
            }
            event_metadata = {**metadata, "batch_index": index, "batch_size": len(events)}
            task_id = str(event_payload.get("task_id") or "-")
            try:
                async with execution_scope(
                    task_id=task_id,
                    case_id=str(event_payload.get("case_id") or "-") if event_payload.get("case_id") else None,
                    event_id=str(event_payload.get("event_id") or "-") if event_payload.get("event_id") else None,
                    node=ExecutionNode.KAFKA_BATCH.value,
                ):
                    await self._event_ingest_service.ingest_event(
                        topic=topic,
                        event_payload=event_payload,
                        metadata=event_metadata,
                    )
            except Exception as exc:
                elog(
                    "error",
                    ExecutionNode.KAFKA_BATCH,
                    "failed to ingest batch event item",
                    outcome="failed",
                    batch_index=index,
                    batch_size=len(events),
                    error=str(exc),
                    event_payload_keys=list(event_payload.keys()),
                )

    @staticmethod
    def _extract_batch_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """从批量事件中提取事件列表。"""
        for key in ("events", "tests", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, dict)]
        raise ValueError("test event batch payload must contain one of: events, tests, items, records")


def register_execution_kafka_handlers(
    registry: KafkaTopicHandlerRegistry,
) -> KafkaTopicHandlerRegistry:
    """向 Kafka topic 路由表注册执行模块处理器。"""
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

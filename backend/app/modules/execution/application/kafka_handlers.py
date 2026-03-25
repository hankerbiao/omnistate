"""执行模块 Kafka 消费处理器。"""

from __future__ import annotations

from typing import Any

from app.modules.execution.application.event_ingest_service import ExecutionEventIngestService
from app.modules.execution.schemas.kafka_events import ExecutionResultEvent, RawTestEventEnvelope
from app.shared.core.logger import log as logger
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
        """处理任务级结果消息。

        Args:
            event: 已按 `ExecutionResultEvent` 解析后的结果消息。
            metadata: Kafka 消费元数据，例如 topic、partition、offset。

        当前实现只做日志记录，没有再驱动任务状态。
        原因是平台当前主要依赖 test-events 中的细粒度事件来推进任务和 case 状态，
        结果消息更多是补充信息或兼容性保留。
        """
        logger.info(
            "Received execution result event: "
            f"task_id={event.task_id}, status={event.status}, offset={metadata.get('offset')}"
        )

    async def handle_test_event(
        self,
        event: RawTestEventEnvelope,
        metadata: dict[str, Any],
    ) -> None:
        """处理测试事件总入口。

        Args:
            event: 外层事件包裹对象，真实业务载荷位于 `event.payload`。
            metadata: Kafka 消费元数据。

        这里先根据 schema 名称判断是单条事件还是批量事件，再分发到不同内部方法。
        如果 schema 不符合平台约定，直接抛错，让上层 consumer 决定是否进入死信。
        """
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
        """消费单条测试事件并交给执行事件服务处理。

        Args:
            topic: 当前 Kafka topic。
            payload: 单条测试事件原始业务载荷。
            metadata: Kafka 消费元数据。

        单条事件是最直接的输入形式，这里只做少量日志，然后透传给
        `ExecutionEventIngestService.ingest_event()`。
        """
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
        """消费批量测试事件，并拆分成多条单事件顺序处理。

        Args:
            topic: 当前 Kafka topic。
            payload: 批量事件载荷，内部通常包含 `events/tests/items/records` 之一。
            metadata: Kafka 消费元数据。

        批量事件不会在 `event_ingest_service` 内部再做二次拆分，所以这里先展开。
        同时会为每条拆出的事件补上单事件 schema，并追加 `batch_index/batch_size`
        元数据，便于后续排查批量包中的具体位置。
        """
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
        """从批量事件中提取事件列表。

        Args:
            payload: 批量消息原始载荷。

        Returns:
            批量中的事件字典列表。

        Raises:
            ValueError: 当载荷里找不到平台支持的批量字段时抛出。

        这里兼容多个常见字段名，是为了适配不同测试框架或上报端可能采用的
        批量封装格式，降低执行平台与具体框架的耦合。
        """
        for key in ("events", "tests", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, dict)]
        raise ValueError("test event batch payload must contain one of: events, tests, items, records")


def register_execution_kafka_handlers(
    registry: KafkaTopicHandlerRegistry,
) -> KafkaTopicHandlerRegistry:
    """向 Kafka topic 路由表注册执行模块处理器。

    Args:
        registry: 全局 Kafka topic handler 注册表。

    Returns:
        注册完成后的同一个 registry，便于链式调用。

    这里把执行模块关心的 topic 和 schema 显式绑定到对应 handler：
    - `result_topic` -> 任务结果消息
    - `test_events_topic` -> 测试事件消息
    """
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

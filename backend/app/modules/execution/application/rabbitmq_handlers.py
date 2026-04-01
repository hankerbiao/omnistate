"""执行模块 RabbitMQ 消费处理器。

复用 Kafka handlers 的核心逻辑，通过事件接入服务统一处理。
支持两种消息格式:
1. 测试事件 (test.event.*) -> 与 Kafka test_events_topic 相同格式
2. 结果消息 (test.result) -> 与 Kafka result_topic 相同格式
"""

from __future__ import annotations

import json
from typing import Any

from app.modules.execution.application.kafka_handlers import ExecutionKafkaHandlers
from app.modules.execution.schemas.kafka_events import ExecutionResultEvent, RawTestEventEnvelope
from app.shared.core.logger import log as logger
from app.shared.rabbitmq.consumer import RabbitMQHandlerRegistry


class ExecutionRabbitMQHandlers:
    """执行模块 RabbitMQ 消费处理器。

    复用 Kafka handlers 的核心逻辑，只做消息格式转换。
    """

    def __init__(self) -> None:
        """初始化事件落库服务。

        内部委托给 ExecutionKafkaHandlers 处理实际业务逻辑。
        """
        self._kafka_handlers = ExecutionKafkaHandlers()

    async def handle_test_event(
        self,
        body: bytes,
        metadata: dict[str, Any],
    ) -> None:
        """处理测试事件，与 Kafka handle_test_event 逻辑相同。

        Args:
            body: RabbitMQ 消息体 (JSON 格式的字节)
            metadata: RabbitMQ 消费元数据

        支持两种消息格式:
        1. 单条事件: schema 结尾为 "-test-event@1"
        2. 批量事件: schema 结尾为 "-test-event-batch@1"
        """
        payload = json.loads(body.decode("utf-8"))
        topic = str(metadata.get("queue") or "rabbitmq-events")

        logger.info(
            "Received RabbitMQ execution test event: "
            f"queue={topic}, routing_key={metadata.get('routing_key')}, "
            f"schema={payload.get('schema')}, delivery_tag={metadata.get('delivery_tag')}"
        )

        # 包装成 Kafka 格式的 envelope
        envelope = RawTestEventEnvelope(payload=payload)

        # 复用 Kafka 的处理逻辑
        # RabbitMQ 没有 topic 概念，用队列名作为标识
        enhanced_metadata = {**metadata, "topic": topic}

        await self._kafka_handlers.handle_test_event(envelope, enhanced_metadata)

    async def handle_result_event(
        self,
        body: bytes,
        metadata: dict[str, Any],
    ) -> None:
        """处理结果消息，与 Kafka handle_result_event 逻辑相同。

        Args:
            body: RabbitMQ 消息体 (JSON 格式的字节)
            metadata: RabbitMQ 消费元数据

        当前实现只做日志记录，与 Kafka 行为一致。
        """
        event_dict = json.loads(body.decode("utf-8"))
        event = ExecutionResultEvent(**event_dict)

        logger.info(
            "Received RabbitMQ execution result event: "
            f"task_id={event.task_id}, status={event.status}, "
            f"routing_key={metadata.get('routing_key')}, delivery_tag={metadata.get('delivery_tag')}"
        )

        # 复用 Kafka 的处理逻辑
        enhanced_metadata = {**metadata, "topic": "rabbitmq-results"}
        await self._kafka_handlers.handle_result_event(event, enhanced_metadata)


def register_execution_rabbitmq_handlers(
    registry: RabbitMQHandlerRegistry,
) -> RabbitMQHandlerRegistry:
    """向 RabbitMQ handler 注册表注册执行模块处理器。

    Args:
        registry: RabbitMQ handler 注册表

    Returns:
        注册完成后的同一个 registry，便于链式调用

    注册以下路由:
    - "test.event.#" -> 测试事件消息 (包括 test.event.progress, test.event.assert 等)
    - "test.result" -> 任务结果消息
    """
    handlers = ExecutionRabbitMQHandlers()
    logger.info("Registering execution RabbitMQ handlers")

    # 注册测试事件处理器 (支持通配符)
    registry.register("test.event.#", handlers.handle_test_event)

    # 注册结果消息处理器
    registry.register("test.result", handlers.handle_result_event)

    return registry


__all__ = [
    "ExecutionRabbitMQHandlers",
    "register_execution_rabbitmq_handlers",
]

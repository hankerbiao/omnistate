"""Dead-letter support for Kafka consumers.

Kafka consumer handler 处理失败时，会把原始消息、错误原因和消费元数据封装成
DeadLetterMessage，再发送到配置的 dead-letter topic，便于后续排查或补偿处理。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.shared.core.logger import log
from app.shared.kafka.producer import KafkaProducerManager


@dataclass(slots=True)
class DeadLetterMessage:
    """结构化死信消息。

    该对象保留失败消息的来源 topic、消息 key、原始 payload、异常信息和 Kafka
    消费元数据，避免只记录日志导致后续无法重放或定位问题。
    """

    topic: str
    key: str | None
    payload: dict[str, Any]
    error_message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    failed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """转换成可发送到 dead-letter topic 的 JSON dict。"""
        return {
            "topic": self.topic,
            "key": self.key,
            "payload": self.payload,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "failed_at": self.failed_at,
        }


class KafkaDeadLetterPublisher:
    """死信消息发布器。

    只负责调用 KafkaProducerManager 写入 dead-letter topic，不包含业务补偿逻辑。
    """

    def __init__(self, producer_manager: KafkaProducerManager) -> None:
        """注入 Kafka producer，复用 consumer runner 启动时维护的生产者实例。"""
        self._producer_manager = producer_manager

    def publish(self, message: DeadLetterMessage) -> bool:
        """发布死信消息。

        Headers 中附带 source_topic 和错误类型，方便下游按来源 topic 或失败类型过滤。
        """
        success = self._producer_manager.send_dead_letter(
            message_key=message.key or "unknown",
            payload=message.to_dict(),
            headers=[
                ("source_topic", message.topic.encode("utf-8")),
                ("error_type", b"consumer_handler_error"),
            ],
        )
        if not success:
            log.error(f"Failed to publish dead-letter message for topic={message.topic}")
        return success

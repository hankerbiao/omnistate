"""Dead-letter support for Kafka consumers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.shared.core.logger import log
from app.shared.kafka.producer import KafkaProducerManager


@dataclass(slots=True)
class DeadLetterMessage:
    """Structured dead-letter payload."""

    topic: str
    key: str | None
    payload: dict[str, Any]
    error_message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    failed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "key": self.key,
            "payload": self.payload,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "failed_at": self.failed_at,
        }


class KafkaDeadLetterPublisher:
    """Publish failed messages to dead-letter topic."""

    def __init__(self, producer_manager: KafkaProducerManager) -> None:
        self._producer_manager = producer_manager

    def publish(self, message: DeadLetterMessage) -> bool:
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

"""Compatibility wrapper for legacy imports."""

from app.shared.kafka.producer import TaskMessage
from app.shared.rabbitmq.producer import RabbitMQProducerManager


__all__ = [
    "RabbitMQMessageManager",
    "TaskMessage",
]


class RabbitMQMessageManager(RabbitMQProducerManager):
    """Backwards-compatible alias for the producer-only manager."""

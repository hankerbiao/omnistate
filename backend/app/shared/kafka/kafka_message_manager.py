"""Compatibility wrapper for legacy imports."""

from app.shared.kafka.producer import KafkaProducerManager, ResultMessage, TaskMessage


__all__ = [
    "KafkaMessageManager",
    "TaskMessage",
    "ResultMessage",
]


class KafkaMessageManager(KafkaProducerManager):
    """Backwards-compatible alias for the producer-only manager."""

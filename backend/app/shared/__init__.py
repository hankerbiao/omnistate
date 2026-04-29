"""共享基础设施与通用能力。"""

from .kafka import (
    KafkaProducerManager,
    TaskMessage,
    ResultMessage,
    KafkaConfig,
    load_kafka_config,
)

__all__ = [
    "KafkaProducerManager",
    "TaskMessage",
    "ResultMessage",
    "KafkaConfig",
    "load_kafka_config",
]

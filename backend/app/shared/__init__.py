"""共享基础设施与通用能力。"""

from .kafka import (
    KafkaMessageManager,
    TaskMessage,
    ResultMessage,
    KafkaConfig,
    load_kafka_config,
)

__all__ = [
    "KafkaMessageManager",
    "TaskMessage",
    "ResultMessage",
    "KafkaConfig",
    "load_kafka_config",
]

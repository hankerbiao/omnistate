"""共享基础设施与通用能力"""

# Kafka 消息管理模块
from .kafka import (
    KafkaMessageManager,
    TaskMessage,
    ResultMessage,
    get_kafka_config,
    get_task_config,
    get_message_config,
    update_config,
    load_from_environment
)

__all__ = [
    # Kafka 消息管理
    'KafkaMessageManager',
    'TaskMessage',
    'ResultMessage',
    'get_kafka_config',
    'get_task_config',
    'get_message_config',
    'update_config',
    'load_from_environment'
]

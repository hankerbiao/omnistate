"""
Kafka 消息管理模块

这个模块提供了完整的 Kafka 消息管理功能，用于任务下发和接收。
"""

from .kafka_message_manager import (
    KafkaMessageManager,
    TaskMessage,
    ResultMessage,
)


from .config import (
    get_kafka_config,
    get_task_config,
    get_message_config,
    update_config,
    load_from_environment
)

__all__ = [
    # 消息管理
    'KafkaMessageManager',
    'TaskMessage',
    'ResultMessage',
    # 配置管理
    'get_kafka_config',
    'get_task_config',
    'get_message_config',
    'update_config',
    'load_from_environment'
]

__version__ = '1.0.0'
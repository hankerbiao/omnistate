"""RabbitMQ 消息管理模块。"""

from app.shared.kafka.producer import TaskMessage

from .config import RabbitMQConfig, load_rabbitmq_config
from .consumer import RabbitMQConsumerRunner, RabbitMQHandlerRegistry
from .producer import RabbitMQProducerManager

__all__ = [
    "RabbitMQConfig",
    "RabbitMQConsumerRunner",
    "RabbitMQHandlerRegistry",
    "RabbitMQProducerManager",
    "TaskMessage",
    "load_rabbitmq_config",
]

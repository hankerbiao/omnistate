"""RabbitMQ 消息管理模块。"""

from app.shared.kafka.producer import TaskMessage

from .config import RabbitMQConfig, load_rabbitmq_config
from .producer import RabbitMQProducerManager

__all__ = [
    "RabbitMQConfig",
    "RabbitMQProducerManager",
    "TaskMessage",
    "load_rabbitmq_config",
]

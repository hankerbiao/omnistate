"""RabbitMQ 消息管理模块。"""

from app.shared.kafka.producer import TaskMessage

from .config import RabbitMQConfig, load_rabbitmq_config
from .producer import RabbitMQProducerManager
from .rabbitmq_message_manager import RabbitMQMessageManager

__all__ = [
    "RabbitMQConfig",
    "RabbitMQProducerManager",
    "RabbitMQMessageManager",
    "TaskMessage",
    "load_rabbitmq_config",
]

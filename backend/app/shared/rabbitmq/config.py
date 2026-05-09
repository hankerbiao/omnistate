"""RabbitMQ 消息队列模块配置。"""

from app.shared.config import RabbitMQConfig, get_settings


def load_rabbitmq_config() -> RabbitMQConfig:
    return get_settings().rabbitmq


__all__ = ["RabbitMQConfig", "load_rabbitmq_config"]

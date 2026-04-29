"""RabbitMQ 消息队列模块配置。

配置从 config.yaml 统一加载，参考 app/shared/config/settings.py
"""

from app.shared.config import RabbitMQConfig, load_rabbitmq_config

__all__ = ["RabbitMQConfig", "load_rabbitmq_config"]

"""RabbitMQ 模块配置。"""

import os
from dataclasses import dataclass, field
from typing import Any


DEFAULT_HOST = "10.32.12.28"
DEFAULT_PORT = 5672
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin@123+"
DEFAULT_VHOST = "/"
DEFAULT_TASK_QUEUE = "dml_task_queue"
DEFAULT_TASK_EXCHANGE = ""
DEFAULT_TASK_ROUTING_KEY = DEFAULT_TASK_QUEUE


@dataclass(slots=True)
class RabbitMQConfig:
    """RabbitMQ 运行时配置。"""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    username: str = DEFAULT_USERNAME
    password: str = DEFAULT_PASSWORD
    virtual_host: str = DEFAULT_VHOST
    task_queue: str = DEFAULT_TASK_QUEUE
    task_exchange: str = DEFAULT_TASK_EXCHANGE
    task_routing_key: str = DEFAULT_TASK_ROUTING_KEY
    heartbeat: int = 60
    blocked_connection_timeout: int = 30
    connection_attempts: int = 3
    retry_delay: float = 2.0
    ssl_options: dict[str, Any] | None = field(default=None)


def load_rabbitmq_config() -> RabbitMQConfig:
    """从环境变量加载 RabbitMQ 配置。"""
    return RabbitMQConfig(
        host=os.getenv("RABBITMQ_HOST", DEFAULT_HOST),
        port=int(os.getenv("RABBITMQ_PORT", str(DEFAULT_PORT))),
        username=os.getenv("RABBITMQ_USERNAME", DEFAULT_USERNAME),
        password=os.getenv("RABBITMQ_PASSWORD", DEFAULT_PASSWORD),
        virtual_host=os.getenv("RABBITMQ_VHOST", DEFAULT_VHOST),
        task_queue=os.getenv("RABBITMQ_TASK_QUEUE", DEFAULT_TASK_QUEUE),
        task_exchange=os.getenv("RABBITMQ_TASK_EXCHANGE", DEFAULT_TASK_EXCHANGE),
        task_routing_key=os.getenv("RABBITMQ_TASK_ROUTING_KEY", DEFAULT_TASK_ROUTING_KEY),
        heartbeat=int(os.getenv("RABBITMQ_HEARTBEAT", "60")),
        blocked_connection_timeout=int(os.getenv("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", "30")),
        connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
        retry_delay=float(os.getenv("RABBITMQ_RETRY_DELAY", "2")),
    )

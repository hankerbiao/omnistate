"""RabbitMQ 模块配置。"""

import os
from dataclasses import dataclass, field
from typing import Any


DEFAULT_HOST = "10.32.12.28"
DEFAULT_PORT = 5672
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin@123+"
DEFAULT_VHOST = "/"

# Producer configuration (task dispatch)
DEFAULT_TASK_QUEUE = "dml_task_queue"
DEFAULT_TASK_EXCHANGE = ""
DEFAULT_TASK_ROUTING_KEY = DEFAULT_TASK_QUEUE

# Consumer configuration (test event ingestion)
DEFAULT_EVENT_QUEUE = "dml_test_events"
DEFAULT_EVENT_EXCHANGE = "dml_test_exchange"
DEFAULT_EVENT_ROUTING_KEY = "test.event.#"
DEFAULT_RESULT_QUEUE = "dml_test_results"
DEFAULT_RESULT_EXCHANGE = "dml_results_exchange"
DEFAULT_RESULT_ROUTING_KEY = "test.result"
DEFAULT_PREFETCH_COUNT = 10


@dataclass(slots=True)
class RabbitMQConfig:
    """RabbitMQ 运行时配置。"""

    # Connection settings
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    username: str = DEFAULT_USERNAME
    password: str = DEFAULT_PASSWORD
    virtual_host: str = DEFAULT_VHOST
    heartbeat: int = 60
    blocked_connection_timeout: int = 30
    connection_attempts: int = 3
    retry_delay: float = 2.0
    ssl_options: dict[str, Any] | None = field(default=None)

    # Producer configuration (task dispatch)
    task_queue: str = DEFAULT_TASK_QUEUE
    task_exchange: str = DEFAULT_TASK_EXCHANGE
    task_routing_key: str = DEFAULT_TASK_ROUTING_KEY

    # Consumer configuration (test event ingestion)
    event_queue: str = DEFAULT_EVENT_QUEUE
    event_exchange: str = DEFAULT_EVENT_EXCHANGE
    event_routing_key: str = DEFAULT_EVENT_ROUTING_KEY
    result_queue: str = DEFAULT_RESULT_QUEUE
    result_exchange: str = DEFAULT_RESULT_EXCHANGE
    result_routing_key: str = DEFAULT_RESULT_ROUTING_KEY
    prefetch_count: int = DEFAULT_PREFETCH_COUNT


def load_rabbitmq_config() -> RabbitMQConfig:
    """从环境变量加载 RabbitMQ 配置。"""
    return RabbitMQConfig(
        # Connection settings
        host=os.getenv("RABBITMQ_HOST", DEFAULT_HOST),
        port=int(os.getenv("RABBITMQ_PORT", str(DEFAULT_PORT))),
        username=os.getenv("RABBITMQ_USERNAME", DEFAULT_USERNAME),
        password=os.getenv("RABBITMQ_PASSWORD", DEFAULT_PASSWORD),
        virtual_host=os.getenv("RABBITMQ_VHOST", DEFAULT_VHOST),
        heartbeat=int(os.getenv("RABBITMQ_HEARTBEAT", "60")),
        blocked_connection_timeout=int(os.getenv("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", "30")),
        connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
        retry_delay=float(os.getenv("RABBITMQ_RETRY_DELAY", "2")),
        # Producer configuration
        task_queue=os.getenv("RABBITMQ_TASK_QUEUE", DEFAULT_TASK_QUEUE),
        task_exchange=os.getenv("RABBITMQ_TASK_EXCHANGE", DEFAULT_TASK_EXCHANGE),
        task_routing_key=os.getenv("RABBITMQ_TASK_ROUTING_KEY", DEFAULT_TASK_ROUTING_KEY),
        # Consumer configuration
        event_queue=os.getenv("RABBITMQ_EVENT_QUEUE", DEFAULT_EVENT_QUEUE),
        event_exchange=os.getenv("RABBITMQ_EVENT_EXCHANGE", DEFAULT_EVENT_EXCHANGE),
        event_routing_key=os.getenv("RABBITMQ_EVENT_ROUTING_KEY", DEFAULT_EVENT_ROUTING_KEY),
        result_queue=os.getenv("RABBITMQ_RESULT_QUEUE", DEFAULT_RESULT_QUEUE),
        result_exchange=os.getenv("RABBITMQ_RESULT_EXCHANGE", DEFAULT_RESULT_EXCHANGE),
        result_routing_key=os.getenv("RABBITMQ_RESULT_ROUTING_KEY", DEFAULT_RESULT_ROUTING_KEY),
        prefetch_count=int(os.getenv("RABBITMQ_PREFETCH_COUNT", str(DEFAULT_PREFETCH_COUNT))),
    )

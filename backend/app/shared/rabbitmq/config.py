"""RabbitMQ 消息队列模块配置。

本模块定义了与 RabbitMQ 服务器通信所需的所有配置参数，包括：
- 连接参数（主机、端口、认证）
- 生产者配置（任务下发）
- 消费者配置（测试事件接收、测试结果接收）

Usage:
    from app.shared.rabbitmq.config import load_rabbitmq_config

    config = load_rabbitmq_config()
"""

import os
from dataclasses import dataclass, field
from typing import Any


# ============================================================================
# 默认连接配置
# ============================================================================
DEFAULT_HOST = "10.32.12.28"          # RabbitMQ 服务器地址
DEFAULT_PORT = 5672                   # RabbitMQ AMQP 协议端口
DEFAULT_USERNAME = "admin"            # 连接用户名
DEFAULT_PASSWORD = "admin@123+"       # 连接密码（测试环境）
DEFAULT_VHOST = "/"                    # 虚拟主机路径

# ============================================================================
# 生产者配置（任务下发）
# 后端 -> 测试代理：下发测试任务
# ============================================================================
DEFAULT_TASK_QUEUE = "dml_task_queue"       # 任务下发队列
DEFAULT_TASK_EXCHANGE = ""                   # 直接使用默认 exchange
DEFAULT_TASK_ROUTING_KEY = DEFAULT_TASK_QUEUE  # 路由键与队列名相同

# ============================================================================
# 消费者配置（测试事件接收）
# 测试代理 -> 后端：上报测试进度事件
# ============================================================================
DEFAULT_EVENT_QUEUE = "dml_test_events"      # 测试事件队列（接收测试代理上报的进度）
DEFAULT_EVENT_EXCHANGE = "dml_test_exchange" # 测试事件交换机
DEFAULT_EVENT_ROUTING_KEY = "test.event.#"   # 通配符匹配所有测试事件

# ============================================================================
# 消费者配置（测试结果接收）
# 测试代理 -> 后端：上报测试结果
# ============================================================================
DEFAULT_RESULT_QUEUE = "dml_test_results"    # 测试结果队列（接收最终测试结果）
DEFAULT_RESULT_EXCHANGE = "dml_results_exchange"  # 测试结果交换机
DEFAULT_RESULT_ROUTING_KEY = "test.result"   # 精确匹配测试结果消息
DEFAULT_PREFETCH_COUNT = 10                  # 消费者预取消息数量（性能调优参数）


@dataclass(slots=True)
class RabbitMQConfig:
    """RabbitMQ 运行时配置。

    配置参数可以通过环境变量覆盖，参考 load_rabbitmq_config() 函数。

    Attributes:
        host: RabbitMQ 服务器主机地址
        port: RabbitMQ AMQP 协议端口（默认 5672）
        username: 连接认证用户名
        password: 连接认证密码
        virtual_host: 虚拟主机路径，用于隔离不同应用的消息
        heartbeat: 心跳检测间隔（秒），用于检测连接是否存活
        blocked_connection_timeout: 连接阻塞超时时间（秒）
        connection_attempts: 连接失败重试次数
        retry_delay: 重试间隔时间（秒）
        ssl_options: SSL/TLS 连接选项，None 表示不使用 SSL
        task_queue/task_exchange/task_routing_key: 任务下发相关配置（生产者）
        event_queue/event_exchange/event_routing_key: 测试事件接收配置（消费者）
        result_queue/result_exchange/result_routing_key: 测试结果接收配置（消费者）
        prefetch_count: 消费者预取消息数量，平衡并发和内存使用
    """

    # =========================================================================
    # 连接参数
    # =========================================================================
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    username: str = DEFAULT_USERNAME
    password: str = DEFAULT_PASSWORD
    virtual_host: str = DEFAULT_VHOST
    heartbeat: int = 60                      # 心跳间隔（秒），0 表示禁用
    blocked_connection_timeout: int = 30     # 连接阻塞超时
    connection_attempts: int = 3             # 连接重试次数
    retry_delay: float = 2.0                 # 重试间隔（秒）
    ssl_options: dict[str, Any] | None = field(default=None)  # TLS 配置

    # =========================================================================
    # 生产者配置（任务下发）
    # =========================================================================
    task_queue: str = DEFAULT_TASK_QUEUE
    task_exchange: str = DEFAULT_TASK_EXCHANGE
    task_routing_key: str = DEFAULT_TASK_ROUTING_KEY

    # =========================================================================
    # 消费者配置（测试事件）
    # =========================================================================
    event_queue: str = DEFAULT_EVENT_QUEUE
    event_exchange: str = DEFAULT_EVENT_EXCHANGE
    event_routing_key: str = DEFAULT_EVENT_ROUTING_KEY

    # =========================================================================
    # 消费者配置（测试结果）
    # =========================================================================
    result_queue: str = DEFAULT_RESULT_QUEUE
    result_exchange: str = DEFAULT_RESULT_EXCHANGE
    result_routing_key: str = DEFAULT_RESULT_ROUTING_KEY
    prefetch_count: int = DEFAULT_PREFETCH_COUNT


def load_rabbitmq_config() -> RabbitMQConfig:
    """从环境变量加载 RabbitMQ 配置。

    环境变量命名规范: RABBITMQ_<SECTION>_<PARAMETER>
    例如: RABBITMQ_HOST, RABBITMQ_TASK_QUEUE, RABBITMQ_PREFETCH_COUNT

    如果环境变量未设置，使用默认值。

    Returns:
        RabbitMQConfig: 包含所有配置参数的配置对象

    Environment Variables:
        连接参数:
            RABBITMQ_HOST: 服务器地址
            RABBITMQ_PORT: 端口号
            RABBITMQ_USERNAME: 用户名
            RABBITMQ_PASSWORD: 密码
            RABBITMQ_VHOST: 虚拟主机
            RABBITMQ_HEARTBEAT: 心跳间隔（秒）
            RABBITMQ_BLOCKED_CONNECTION_TIMEOUT: 连接超时
            RABBITMQ_CONNECTION_ATTEMPTS: 重试次数
            RABBITMQ_RETRY_DELAY: 重试间隔
        生产者参数:
            RABBITMQ_TASK_QUEUE: 任务队列名
            RABBITMQ_TASK_EXCHANGE: 任务交换机
            RABBITMQ_TASK_ROUTING_KEY: 任务路由键
        消费者参数:
            RABBITMQ_EVENT_QUEUE: 事件队列名
            RABBITMQ_EVENT_EXCHANGE: 事件交换机
            RABBITMQ_EVENT_ROUTING_KEY: 事件路由键
            RABBITMQ_RESULT_QUEUE: 结果队列名
            RABBITMQ_RESULT_EXCHANGE: 结果交换机
            RABBITMQ_RESULT_ROUTING_KEY: 结果路由键
            RABBITMQ_PREFETCH_COUNT: 预取数量
    """
    return RabbitMQConfig(
        # 连接参数
        host=os.getenv("RABBITMQ_HOST", DEFAULT_HOST),
        port=int(os.getenv("RABBITMQ_PORT", str(DEFAULT_PORT))),
        username=os.getenv("RABBITMQ_USERNAME", DEFAULT_USERNAME),
        password=os.getenv("RABBITMQ_PASSWORD", DEFAULT_PASSWORD),
        virtual_host=os.getenv("RABBITMQ_VHOST", DEFAULT_VHOST),
        heartbeat=int(os.getenv("RABBITMQ_HEARTBEAT", "60")),
        blocked_connection_timeout=int(os.getenv("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", "30")),
        connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
        retry_delay=float(os.getenv("RABBITMQ_RETRY_DELAY", "2")),
        # 生产者配置（任务下发）
        task_queue=os.getenv("RABBITMQ_TASK_QUEUE", DEFAULT_TASK_QUEUE),
        task_exchange=os.getenv("RABBITMQ_TASK_EXCHANGE", DEFAULT_TASK_EXCHANGE),
        task_routing_key=os.getenv("RABBITMQ_TASK_ROUTING_KEY", DEFAULT_TASK_ROUTING_KEY),
        # 消费者配置（事件接收）
        event_queue=os.getenv("RABBITMQ_EVENT_QUEUE", DEFAULT_EVENT_QUEUE),
        event_exchange=os.getenv("RABBITMQ_EVENT_EXCHANGE", DEFAULT_EVENT_EXCHANGE),
        event_routing_key=os.getenv("RABBITMQ_EVENT_ROUTING_KEY", DEFAULT_EVENT_ROUTING_KEY),
        # 消费者配置（结果接收）
        result_queue=os.getenv("RABBITMQ_RESULT_QUEUE", DEFAULT_RESULT_QUEUE),
        result_exchange=os.getenv("RABBITMQ_RESULT_EXCHANGE", DEFAULT_RESULT_EXCHANGE),
        result_routing_key=os.getenv("RABBITMQ_RESULT_ROUTING_KEY", DEFAULT_RESULT_ROUTING_KEY),
        prefetch_count=int(os.getenv("RABBITMQ_PREFETCH_COUNT", str(DEFAULT_PREFETCH_COUNT))),
    )

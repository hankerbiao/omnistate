"""RabbitMQ 生产者运行时模块。

负责 RabbitMQ 连接管理和消息发送功能。
使用 pika 库实现同步的 AMQP 客户端。
"""

from __future__ import annotations

import json
import ssl
from datetime import UTC, datetime
from typing import Any

from app.shared.core.logger import log
from app.shared.kafka.producer import TaskMessage
from app.shared.rabbitmq.config import RabbitMQConfig, load_rabbitmq_config

try:
    import pika
    from pika.credentials import PlainCredentials
    from pika.exceptions import AMQPError
except ImportError:  # pragma: no cover - 当 pika 未安装时的降级处理
    pika = None
    PlainCredentials = None
    AMQPError = Exception


class RabbitMQProducerManager:
    """RabbitMQ 生产者管理器。

    只负责 RabbitMQ 生产者生命周期与消息发送。
    支持以下功能：
    - 自动重连机制
    - SSL/TLS 连接
    - 消息持久化
    - 优先级队列
    - 健康检查
    """

    def __init__(self, config: RabbitMQConfig | None = None) -> None:
        """初始化生产者管理器。

        Args:
            config: RabbitMQ 配置，若为 None 则从配置文件加载
        """
        self.config = config or load_rabbitmq_config()
        self.connection = None  # AMQP 连接对象
        self.channel = None     # AMQP 通道对象
        self.is_running = False # 运行状态标志

    def _create_connection(self):
        """创建 AMQP 连接。

        根据配置创建到 RabbitMQ 服务器的连接，支持 SSL。

        Returns:
            pika.BlockingConnection: AMQP 连接对象

        Raises:
            RuntimeError: 当 pika 库未安装时
        """
        if pika is None or PlainCredentials is None:
            raise RuntimeError("需要安装 pika 库才能使用 RabbitMQ 分发功能")

        # SSL 配置
        ssl_options = None
        if self.config.ssl_enabled:
            ssl_options = pika.SSLOptions(
                context=ssl.create_default_context(),
                server_hostname=self.config.host,
            )

        # 连接参数
        parameters = pika.ConnectionParameters(
            host=self.config.host,
            port=self.config.port,
            virtual_host=self.config.virtual_host,
            credentials=PlainCredentials(
                username=self.config.username,
                password=self.config.password,
            ),
            heartbeat=self.config.heartbeat,
            blocked_connection_timeout=self.config.blocked_connection_timeout,
            connection_attempts=self.config.connection_attempts,
            retry_delay=self.config.retry_delay,
            ssl_options=ssl_options,
        )
        return pika.BlockingConnection(parameters)

    def start(self) -> None:
        """启动生产者管理器。

        建立与 RabbitMQ 的连接和通道，并声明任务队列。
        """
        if self._is_connection_ready():
            return

        self.connection = self._create_connection()
        self.channel = self.connection.channel()

        # 开启消息确认模式，确保消息可靠投递
        self.channel.confirm_delivery()

        # 声明持久化队列
        self.channel.queue_declare(queue=self.config.task_queue, durable=True)

        self.is_running = True
        log.info("RabbitMQ 生产者管理器已启动")

    def stop(self) -> None:
        """停止生产者管理器。

        关闭通道和连接，释放资源。
        """
        # 关闭通道
        if self.channel is not None:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None

        # 关闭连接
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

        self.is_running = False
        log.info("RabbitMQ 生产者管理器已停止")

    def _is_connection_ready(self) -> bool:
        """检查连接是否就绪。

        检查连接和通道是否已建立且处于开放状态。

        Returns:
            bool: 连接就绪返回 True，否则返回 False
        """
        return (
            self.is_running
            and self.connection is not None
            and self.channel is not None
            and hasattr(self.connection, "is_open")
            and self.connection.is_open
            and hasattr(self.channel, "is_open")
            and self.channel.is_open
        )

    def _ensure_connection_ready(self) -> bool:
        """确保连接就绪，必要时自动重连。

        Returns:
            bool: 重连成功后返回 True，失败返回 False
        """
        if self._is_connection_ready():
            return True

        try:
            self.stop()
            self.start()
            return self._is_connection_ready()
        except Exception as exc:
            log.error(f"RabbitMQ 生产者管理器恢复失败: {exc}")
            return False

    def send_task(self, task_message: TaskMessage, priority: int | None = None) -> bool:
        """发送任务消息到 RabbitMQ。

        Args:
            task_message: 任务消息对象
            priority: 消息优先级，若为 None 则使用消息自身的优先级

        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        # 确保连接就绪
        if not self._ensure_connection_ready():
            log.error("RabbitMQ 生产者管理器未运行")
            return False

        # 确定优先级
        message_priority = task_message.priority if priority is None else priority

        # 构建消息属性
        properties = None
        if pika is not None:
            properties = pika.BasicProperties(
                delivery_mode=2,  # 消息持久化到磁盘
                content_type="application/json",
                content_encoding="utf-8",
                priority=message_priority,
                headers={
                    "task_type": task_message.task_type,
                    "source": task_message.source,
                },
                message_id=task_message.task_id,
                timestamp=int(datetime.now(UTC).timestamp()),
            )

        try:
            # 发布消息
            self.channel.basic_publish(
                exchange=self.config.task_exchange,
                routing_key=self.config.task_routing_key,
                body=json.dumps(
                    task_message.task_data,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
                properties=properties,
                mandatory=False,
            )
            log.info(f"任务成功发送到 RabbitMQ: {task_message.task_id}")
            return True
        except AMQPError as exc:
            log.error(f"RabbitMQ 发送失败, task_id={task_message.task_id}, error={exc}")
            return False
        except Exception as exc:
            log.error(f"RabbitMQ 发送失败, task_id={task_message.task_id}, error={exc}")
            return False

    def health_check(self) -> dict[str, Any]:
        """健康检查。

        返回生产者的健康状态信息。

        Returns:
            dict: 包含组件状态、连接详情等信息的字典
        """
        if not self.is_running:
            return {
                "component": "rabbitmq_producer_manager",
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "STOPPED",
                "message": "RabbitMQ 生产者管理器未运行",
            }

        return {
            "component": "rabbitmq_producer_manager",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "HEALTHY" if self._is_connection_ready() else "DEGRADED",
            "message": "RabbitMQ 生产者管理器运行正常",
            "details": {
                "host": self.config.host,
                "port": self.config.port,
                "virtual_host": self.config.virtual_host,
                "task_queue": self.config.task_queue,
                "task_exchange": self.config.task_exchange,
                "task_routing_key": self.config.task_routing_key,
                "channel_available": self.channel is not None,
                "channel_open": getattr(self.channel, "is_open", False),
                "connection_open": getattr(self.connection, "is_open", False),
            },
        }

    def __enter__(self) -> "RabbitMQProducerManager":
        """上下文管理器入口，启动生产者。"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出，停止生产者。"""
        self.stop()
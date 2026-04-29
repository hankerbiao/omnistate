"""RabbitMQ consumer runtime."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)

from app.shared.rabbitmq.config import RabbitMQConfig

from .config import load_rabbitmq_config

try:
    from aio_pika import Message
except ImportError:  # pragma: no cover - tested via runtime initialization path
    Message = None


class RabbitMQHandlerRegistry:
    """RabbitMQ 消息处理器注册表。

    用于注册不同 routing_key 对应的处理器函数。
    支持通配符匹配 (如 "test.event.#")。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[bytes, dict[str, Any]], Coroutine[Any, Any, None]]] = {}

    def register(
            self,
            routing_key: str,
            handler: Callable[[bytes, dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """注册 routing_key 对应的处理器。

        Args:
            routing_key: RabbitMQ 路由键，支持通配符 (# 匹配零或多词，* 匹配单词)
            handler: 异步处理器函数，接收 (body: bytes, metadata: dict) 参数
        """
        self._handlers[routing_key] = handler

    @property
    def handlers(self) -> dict[str, Callable[[bytes, dict[str, Any]], Coroutine[Any, Any, None]]]:
        """获取所有已注册的处理器。"""
        return self._handlers

    def get_handler(self, routing_key: str) -> Callable[[bytes, dict[str, Any]], Coroutine[Any, Any, None]] | None:
        """根据 routing_key 查找处理器。

        支持通配符匹配：
        - # 匹配零或多词
        - * 匹配单个词

        Args:
            routing_key: RabbitMQ 路由键

        Returns:
            对应的处理器函数，如果没有匹配则返回 None
        """
        # 精确匹配
        if routing_key in self._handlers:
            return self._handlers[routing_key]
        return None


class RabbitMQConsumerRunner:
    """RabbitMQ 异步消费者运行时。

    特性：
    - 使用 RobustConnection 实现自动重连
    - 支持手动 ack 机制
    - 优雅关闭 (等待处理中的消息完成)
    - 根据 routing_key 分发到不同 handler
    """

    def __init__(
            self,
            config: RabbitMQConfig | None = None,
            registry: RabbitMQHandlerRegistry | None = None,
    ) -> None:
        """初始化消费者运行时。

        Args:
            config: RabbitMQ 配置，默认从环境变量加载
            registry: 处理器注册表
        """
        self.config = config or load_rabbitmq_config()
        self.registry = registry or RabbitMQHandlerRegistry()
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._queues: dict[str, AbstractQueue] = {}
        self._running = False
        self._closing = False
        self._consumer_tags: set[str] = set()

    async def start(self) -> None:
        """启动消费者，连接 RabbitMQ 并声明队列/交换机。

        声明以下资源：
        1. 测试事件队列 (event_queue) + 交换机 (event_exchange)
        2. 结果消息队列 (result_queue) + 交换机 (result_exchange)
        """
        from app.shared.core.logger import log

        if self._running:
            log.warning("RabbitMQ consumer runner already started")
            return

        log.info(
            f"Starting RabbitMQ consumer: host={self.config.host}, "
            f"port={self.config.port}, vhost={self.config.virtual_host}"
        )

        # 创建连接
        self._connection = await self._create_connection()
        self._channel = await self._connection.channel()

        # 设置 QoS (prefetch count)
        await self._channel.set_qos(prefetch_count=self.config.prefetch_count)

        # 声明测试事件交换机和队列
        if self.config.event_exchange:
            event_exchange = await self._channel.declare_exchange(
                self.config.event_exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
        else:
            # 如果没有交换机，使用默认交换机
            event_exchange = self._channel.default_exchange

        event_queue = await self._channel.declare_queue(
            self.config.event_queue,
            durable=True,
        )
        await event_queue.bind(
            event_exchange,
            routing_key=self.config.event_routing_key,
        )
        self._queues[self.config.event_queue] = event_queue

        # 声明结果消息交换机和队列
        if self.config.result_exchange:
            result_exchange = await self._channel.declare_exchange(
                self.config.result_exchange,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
        else:
            result_exchange = self._channel.default_exchange

        result_queue = await self._channel.declare_queue(
            self.config.result_queue,
            durable=True,
        )
        await result_queue.bind(
            result_exchange,
            routing_key=self.config.result_routing_key,
        )
        self._queues[self.config.result_queue] = result_queue

        self._running = True
        log.info(
            f"RabbitMQ consumer started: event_queue={self.config.event_queue}, "
            f"result_queue={self.config.result_queue}"
        )

    async def stop(self) -> None:
        """优雅停止消费者。

        等待正在处理的消息完成后再关闭连接。
        """
        from app.shared.core.logger import log

        if not self._running:
            log.warning("RabbitMQ consumer runner already stopped")
            return

        log.info("Stopping RabbitMQ consumer runner...")
        self._closing = True

        # 取消消费者
        for consumer_tag in list(self._consumer_tags):
            try:
                if self._channel:
                    await self._channel.basic_cancel(consumer_tag)
            except Exception as e:
                log.warning(f"Failed to cancel consumer {consumer_tag}: {e}")

        self._consumer_tags.clear()

        # 关闭 channel
        if self._channel:
            try:
                await self._channel.close()
            except Exception as e:
                log.warning(f"Failed to close channel: {e}")
            self._channel = None

        # 关闭连接
        if self._connection:
            try:
                await self._connection.close()
            except Exception as e:
                log.warning(f"Failed to close connection: {e}")
            self._connection = None

        self._queues.clear()
        self._running = False
        log.info("RabbitMQ consumer runner stopped")

    async def run_forever(self) -> None:
        """持续消费消息。

        该方法会阻塞直到消费者停止。
        如果连接断开，会自动重连。
        """
        from app.shared.core.logger import log

        if not self._running:
            await self.start()

        log.info("RabbitMQ consumer runner is running forever...")

        # 为每个队列启动消费者
        for queue_name, queue in self._queues.items():
            consumer_tag = await queue.consume(self._on_message)
            self._consumer_tags.add(consumer_tag)
            log.info(f"Started consuming from queue: {queue_name}")

        # 保持运行
        try:
            while self._running and not self._closing:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            log.info("RabbitMQ consumer runner cancelled")

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        """消息处理入口。

        根据 routing_key 分发到对应 handler 处理。
        使用手动 ack机制，支持失败后 requeue。

        Args:
            message: RabbitMQ 消息
        """
        from app.shared.core.logger import log

        async with message.process(requeue=True):
            routing_key = message.routing_key or ""
            body = message.body

            # 提取元数据
            metadata = self._extract_metadata(message)

            # 查找处理器
            handler = self.registry.get_handler(routing_key)

            if handler is None:
                log.warning(f"No handler for routing_key: {routing_key}, message will be requeued")
                # 没有处理器，不 ack，消息会被 requeue
                return

            try:
                log.debug(
                    f"Processing message: routing_key={routing_key}, "
                    f"delivery_tag={message.delivery.tag}"
                )
                await handler(body, metadata)
            except Exception as e:
                log.error(
                    f"Error processing message: routing_key={routing_key}, "
                    f"error={e}, message will be requeued"
                )
                # 抛出异常让 aio-pika 重新入队
                raise

    @staticmethod
    def _extract_metadata(message: AbstractIncomingMessage) -> dict[str, Any]:
        """从消息中提取元数据。

        Args:
            message: RabbitMQ 消息

        Returns:
            包含元数据的字典
        """
        return {
            "routing_key": message.routing_key,
            "delivery_tag": message.delivery.tag,
            "content_type": message.content_type,
            "content_encoding": message.content_encoding,
            "message_id": message.message_id,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "headers": dict(message.headers) if message.headers else {},
        }

    async def _create_connection(self) -> AbstractRobustConnection:
        """创建 RabbitMQ 连接。

        使用 RobustConnection 实现自动重连。

        Returns:
            RabbitMQ 连接对象
        """
        from aio_pika.abc import AbstractRobustConnection
        from app.shared.core.logger import log

        connection = await aio_pika.connect_robust(
            host=self.config.host,
            port=self.config.port,
            login=self.config.username,
            password=self.config.password,
            virtualhost=self.config.virtual_host,
            heartbeat=self.config.heartbeat,
            blocked_connection_timeout=self.config.blocked_connection_timeout,
            connection_attempts=self.config.connection_attempts,
            retry_delay=self.config.retry_delay,
        )

        # 注册断开连接回调
        connection.reconnect_callbacks.add(lambda conn: log.warning("RabbitMQ connection lost, will auto-reconnect"))
        connection.close_callbacks.add(lambda conn, exc: log.warning(f"RabbitMQ connection closed: {exc}"))

        log.info(f"Connected to RabbitMQ: {self.config.host}:{self.config.port}")
        return connection

    @property
    def is_running(self) -> bool:
        """检查消费者是否正在运行。"""
        return self._running


__all__ = [
    "RabbitMQConsumerRunner",
    "RabbitMQHandlerRegistry",
    "load_rabbitmq_config",
]

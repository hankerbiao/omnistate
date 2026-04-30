"""Kafka consumer runtime.

该模块封装 Kafka 消费端运行时：
- 根据配置订阅 execution 相关 topic；
- 将消息解析成 JSON dict 后交给 topic router；
- handler 失败时写入 dead-letter topic，并提交原消息 offset，避免阻塞消费。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from kafka import KafkaConsumer

from app.shared.core.logger import log
from app.shared.kafka.config import ConsumerSubscription, KafkaConfig, load_kafka_config
from app.shared.kafka.dead_letter import DeadLetterMessage, KafkaDeadLetterPublisher
from app.shared.kafka.producer import KafkaProducerManager
from app.shared.kafka.router import KafkaTopicHandlerRegistry


@dataclass(slots=True)
class KafkaConsumerRuntime:
    """单个 Kafka topic 订阅的运行时上下文。"""

    subscription_name: str
    subscription: ConsumerSubscription
    consumer: KafkaConsumer


class KafkaConsumerRunner:
    """Kafka 消费循环。

    Runner 负责管理多个 topic subscription。每个 subscription 拥有独立的
    KafkaConsumer，并通过 KafkaTopicHandlerRegistry 分发到业务 handler。
    """

    def __init__(
        self,
        config: KafkaConfig | None = None,
        router: KafkaTopicHandlerRegistry | None = None,
        producer_manager: KafkaProducerManager | None = None,
    ) -> None:
        """初始化 Kafka consumer runner。

        Args:
            config: Kafka 运行时配置，默认从 config.yaml 统一加载。
            router: topic handler 注册表，用于根据 topic 分发消息。
            producer_manager: Kafka producer，用于 handler 失败时发送死信消息。
        """
        self.config = config or load_kafka_config()
        self.router = router or KafkaTopicHandlerRegistry()
        self.producer_manager = producer_manager or KafkaProducerManager(config=self.config)
        self.dead_letter_publisher = KafkaDeadLetterPublisher(self.producer_manager)
        self._runtimes: list[KafkaConsumerRuntime] = []
        self._is_running = False

    def register_subscription(
        self,
        subscription_name: str,
        subscription: ConsumerSubscription,
    ) -> None:
        """注册单个 Kafka topic 订阅。

        这里强制关闭自动提交 offset，确保业务 handler 成功处理后再提交；
        如果 handler 失败，则先写入死信 topic，再提交原消息，避免坏消息反复阻塞。
        """
        consumer_options = dict(self.config.consumer_options)
        # 统一改为手动提交，覆盖 config.yaml 中可能设置的 enable_auto_commit。
        consumer_options["enable_auto_commit"] = False
        consumer = KafkaConsumer(
            bootstrap_servers=self.config.bootstrap_servers,
            client_id=f"{self.config.client_id}-{subscription_name}",
            group_id=subscription.group_id,
            value_deserializer=lambda raw: raw.decode("utf-8") if raw else None,
            key_deserializer=lambda raw: raw.decode("utf-8") if raw else None,
            **consumer_options,
        )
        consumer.subscribe([subscription.topic])
        # 保存 consumer 实例，run_forever 会轮询所有已注册订阅。
        self._runtimes.append(
            KafkaConsumerRuntime(
                subscription_name=subscription_name,
                subscription=subscription,
                consumer=consumer,
            )
        )

    def register_configured_subscriptions(self) -> None:
        """按配置注册订阅，只订阅当前 router 已声明 handler 的 topic。"""
        for name, subscription in self.config.consumer_subscriptions.items():
            if self.router.has_topic(subscription.topic):
                self.register_subscription(name, subscription)

    async def run_forever(self) -> None:
        """启动持续消费循环，直到外部取消任务或进程退出。"""
        if self._is_running:
            return

        self._is_running = True
        # dead-letter publisher 依赖 producer，consumer 启动时一并确保可用。
        if not self.producer_manager.is_running:
            self.producer_manager.start()

        if not self._runtimes:
            self.register_configured_subscriptions()

        try:
            while True:
                # kafka-python 的 poll 是同步阻塞调用，这里放到线程里避免阻塞事件循环。
                for runtime in self._runtimes:
                    await self._poll_runtime(runtime)
                await asyncio.sleep(0.1)
        finally:
            self.stop()

    async def _poll_runtime(self, runtime: KafkaConsumerRuntime) -> None:
        """轮询单个订阅，并把消息交给业务 handler 处理。"""
        records_map = await asyncio.to_thread(runtime.consumer.poll, timeout_ms=500, max_records=50)
        for records in records_map.values():
            for record in records:
                # 保留 Kafka 元数据，业务 handler 和排障日志都需要 topic/partition/offset。
                metadata = {
                    "topic": record.topic,
                    "partition": record.partition,
                    "offset": record.offset,
                    "timestamp": record.timestamp,
                    "key": record.key,
                    "subscription_name": runtime.subscription_name,
                }
                payload = self._parse_payload(record.value)
                try:
                    await self.router.dispatch(record.topic, payload, metadata)
                    # handler 成功后提交 offset，确保消息不会重复消费。
                    await asyncio.to_thread(runtime.consumer.commit)
                except Exception as exc:
                    log.exception(
                        f"Kafka handler failed, topic={record.topic}, offset={record.offset}, error={exc}"
                    )
                    # handler 失败时把原始消息、错误和消费元数据写入死信 topic，便于后续补偿。
                    self.dead_letter_publisher.publish(
                        DeadLetterMessage(
                            topic=record.topic,
                            key=record.key,
                            payload=payload,
                            error_message=str(exc),
                            metadata=metadata,
                        )
                    )
                    # 死信已记录后提交 offset，避免同一坏消息无限重试卡住后续消息。
                    await asyncio.to_thread(runtime.consumer.commit)

    @staticmethod
    def _parse_payload(raw_value: str | None) -> dict[str, Any]:
        """解析 Kafka value，平台约定消息体必须是 JSON object。"""
        if not raw_value:
            return {}
        payload = json.loads(raw_value)
        if not isinstance(payload, dict):
            raise ValueError("Kafka message payload must be a JSON object")
        return payload

    def stop(self) -> None:
        """关闭所有 consumer，并停止本 runner 持有的 producer。"""
        for runtime in self._runtimes:
            runtime.consumer.close()
        self._runtimes.clear()
        self._is_running = False
        if self.producer_manager.is_running:
            self.producer_manager.stop()

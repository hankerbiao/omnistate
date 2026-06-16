"""Kafka consumer runtime."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from kafka import KafkaConsumer

from app.shared.context import trace_scope
from app.shared.core.logger import log
from app.shared.kafka.config import ConsumerSubscription, KafkaConfig, load_kafka_config
from app.shared.kafka.dead_letter import DeadLetterMessage, KafkaDeadLetterPublisher
from app.shared.kafka.producer import KafkaProducerManager
from app.shared.kafka.router import KafkaTopicHandlerRegistry

MAX_CONSECUTIVE_DLQ_FAILURES = 5
CONSUMER_CLOSE_TIMEOUT_SEC = 10.0


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
        self._dlq_fail_count = 0

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
        """启动持续消费循环。"""
        if self._is_running:
            return

        self._is_running = True
        if not self.producer_manager.is_running:
            self.producer_manager.start()

        if not self._runtimes:
            self.register_configured_subscriptions()

        try:
            while True:
                had_messages = False
                for runtime in self._runtimes:
                    had_messages |= await self._poll_runtime(runtime)
                if not had_messages:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0)
        finally:
            self.stop()

    async def _poll_runtime(self, runtime: KafkaConsumerRuntime) -> bool:
        """轮询单个订阅，返回是否有消息被处理。"""
        records_map = await asyncio.to_thread(runtime.consumer.poll, timeout_ms=500, max_records=50)
        has_messages = False
        for records in records_map.values():
            for record in records:
                has_messages = True
                metadata = {
                    "topic": record.topic,
                    "partition": record.partition,
                    "offset": record.offset,
                    "timestamp": record.timestamp,
                    "key": record.key,
                    "subscription_name": runtime.subscription_name,
                }
                payload = self._parse_payload(record.value)
                request_id = f"kafka:{record.topic}:{record.partition}:{record.offset}"
                try:
                    async with trace_scope(request_id=request_id):
                        await self.router.dispatch(record.topic, payload, metadata)
                    await asyncio.to_thread(runtime.consumer.commit)
                    self._dlq_fail_count = 0
                except Exception as exc:
                    log.exception(
                        f"Kafka handler failed, topic={record.topic}, offset={record.offset}, error={exc}"
                    )
                    dlq_success = await self.dead_letter_publisher.publish(
                        DeadLetterMessage(
                            topic=record.topic,
                            key=record.key,
                            payload=payload,
                            error_message=str(exc),
                            metadata=metadata,
                        )
                    )
                    if dlq_success:
                        await asyncio.to_thread(runtime.consumer.commit)
                        self._dlq_fail_count = 0
                    else:
                        self._dlq_fail_count += 1
                        if self._dlq_fail_count >= MAX_CONSECUTIVE_DLQ_FAILURES:
                            log.critical(
                                f"DLQ publish failed {self._dlq_fail_count} consecutive times. "
                                f"Pausing consumer to prevent tight retry loop. "
                                f"Last topic={record.topic}, offset={record.offset}"
                            )
                            self._dlq_fail_count = 0
                            await asyncio.sleep(5)
                            await asyncio.to_thread(runtime.consumer.commit)
                        else:
                            log.error(
                                f"DLQ publish failed ({self._dlq_fail_count}/{MAX_CONSECUTIVE_DLQ_FAILURES}), "
                                f"offset NOT committed: topic={record.topic}, offset={record.offset}"
                            )
        return has_messages

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
        """关闭所有 consumer 并停止 producer。"""
        for runtime in self._runtimes:
            try:
                runtime.consumer.close(autocommit=False)
            except Exception:
                log.exception(f"Error closing consumer for {runtime.subscription_name}")
        self._runtimes.clear()
        self._is_running = False
        if self.producer_manager.is_running:
            self.producer_manager.stop()

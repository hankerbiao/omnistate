"""Kafka consumer runtime."""

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
    """Runtime object for a single topic subscription."""

    subscription_name: str
    subscription: ConsumerSubscription
    consumer: KafkaConsumer


class KafkaConsumerRunner:
    """Consume subscribed topics and dispatch validated events to handlers."""

    def __init__(
        self,
        config: KafkaConfig | None = None,
        router: KafkaTopicHandlerRegistry | None = None,
        producer_manager: KafkaProducerManager | None = None,
    ) -> None:
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
        consumer_options = dict(self.config.consumer_options)
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
        self._runtimes.append(
            KafkaConsumerRuntime(
                subscription_name=subscription_name,
                subscription=subscription,
                consumer=consumer,
            )
        )

    def register_configured_subscriptions(self) -> None:
        for name, subscription in self.config.consumer_subscriptions.items():
            if self.router.has_topic(subscription.topic):
                self.register_subscription(name, subscription)

    async def run_forever(self) -> None:
        if self._is_running:
            return

        self._is_running = True
        if not self.producer_manager.is_running:
            self.producer_manager.start()

        if not self._runtimes:
            self.register_configured_subscriptions()

        try:
            while True:
                for runtime in self._runtimes:
                    await self._poll_runtime(runtime)
                await asyncio.sleep(0.1)
        finally:
            self.stop()

    async def _poll_runtime(self, runtime: KafkaConsumerRuntime) -> None:
        records_map = await asyncio.to_thread(runtime.consumer.poll, timeout_ms=500, max_records=50)
        for records in records_map.values():
            for record in records:
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
                    await asyncio.to_thread(runtime.consumer.commit)
                except Exception as exc:
                    log.exception(
                        f"Kafka handler failed, topic={record.topic}, offset={record.offset}, error={exc}"
                    )
                    self.dead_letter_publisher.publish(
                        DeadLetterMessage(
                            topic=record.topic,
                            key=record.key,
                            payload=payload,
                            error_message=str(exc),
                            metadata=metadata,
                        )
                    )
                    await asyncio.to_thread(runtime.consumer.commit)

    @staticmethod
    def _parse_payload(raw_value: str | None) -> dict[str, Any]:
        if not raw_value:
            return {}
        payload = json.loads(raw_value)
        if not isinstance(payload, dict):
            raise ValueError("Kafka message payload must be a JSON object")
        return payload

    def stop(self) -> None:
        for runtime in self._runtimes:
            runtime.consumer.close()
        self._runtimes.clear()
        self._is_running = False
        if self.producer_manager.is_running:
            self.producer_manager.stop()

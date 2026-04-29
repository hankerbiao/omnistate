"""Kafka 模块配置。

配置从 config.yaml 统一加载，参考 app/shared/config/settings.py
"""

from dataclasses import dataclass, field
from typing import Any

from app.shared.config import KafkaConfig as BaseKafkaConfig


@dataclass(slots=True)
class ConsumerSubscription:
    """单个 consumer 订阅配置。"""

    topic: str
    group_id: str
    parser: str = "json"
    dead_letter_topic: str | None = None


@dataclass(slots=True)
class KafkaConfig:
    """Kafka 运行时配置。

    整合基础配置和旧接口所需的 consumer_subscriptions。
    """

    # 基础配置属性
    bootstrap_servers: list[str] = field(default_factory=lambda: ["localhost:9092"])
    client_id: str = "dmlv4-shard"
    result_topic: str = "dmlv4.results"
    dead_letter_topic: str = "dmlv4.deadletter"
    test_events_topic: str = "test-events"
    execution_result_group_id: str = "dmlv4-execution-result-consumers"
    test_events_group_id: str = "dmlv4-test-events-consumers"
    producer_options: dict[str, Any] = field(default_factory=lambda: {
        "acks": "all",
        "retries": 3,
        "batch_size": 16384,
        "linger_ms": 10,
        "buffer_memory": 33554432,
    })
    consumer_options: dict[str, Any] = field(default_factory=lambda: {
        "auto_offset_reset": "earliest",
        "enable_auto_commit": True,
        "session_timeout_ms": 30000,
        "heartbeat_interval_ms": 3000,
        "max_poll_records": 100,
        "consumer_timeout_ms": 1000,
    })

    # 扩展属性（兼容旧接口）
    consumer_subscriptions: dict[str, ConsumerSubscription] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后设置默认的 consumer_subscriptions。"""
        if not self.consumer_subscriptions:
            self.consumer_subscriptions = {
                "execution_result": ConsumerSubscription(
                    topic=self.result_topic,
                    group_id=self.execution_result_group_id,
                    dead_letter_topic=self.dead_letter_topic,
                ),
                "test_events": ConsumerSubscription(
                    topic=self.test_events_topic,
                    group_id=self.test_events_group_id,
                    dead_letter_topic=self.dead_letter_topic,
                ),
            }


def load_kafka_config() -> KafkaConfig:
    """从 YAML 加载 Kafka 配置（兼容旧接口）。"""
    from app.shared.config import get_settings
    settings = get_settings()
    return KafkaConfig(
        bootstrap_servers=settings.kafka.bootstrap_servers,
        client_id=settings.kafka.client_id,
        result_topic=settings.kafka.result_topic,
        dead_letter_topic=settings.kafka.dead_letter_topic,
        test_events_topic=settings.kafka.test_events_topic,
        execution_result_group_id=settings.kafka.execution_result_group_id,
        test_events_group_id=settings.kafka.test_events_group_id,
        producer_options=settings.kafka.producer_options.model_dump(),
        consumer_options=settings.kafka.consumer_options.model_dump(),
    )


__all__ = ["KafkaConfig", "ConsumerSubscription", "load_kafka_config"]
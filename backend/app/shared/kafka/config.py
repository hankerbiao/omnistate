"""Kafka 模块配置适配层。

Kafka 配置来自进程启动时安装的 MongoDB 运行配置快照。本模块仅把统一
Settings 模型转换为 Kafka 运行时结构。
"""

from dataclasses import dataclass, field
from typing import Any

from app.shared.config import KafkaConfig as BaseKafkaConfig, get_settings


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

    该对象不定义默认值，避免与 `app.shared.config.settings.KafkaConfig`
    形成第二套配置来源。所有字段都由统一 settings 加载后传入。
    """

    bootstrap_servers: list[str]
    client_id: str
    result_topic: str
    dead_letter_topic: str
    test_events_topic: str
    test_events_group_id: str
    producer_options: dict[str, Any]
    consumer_options: dict[str, Any]
    consumer_subscriptions: dict[str, ConsumerSubscription] = field(default_factory=dict)

    def __post_init__(self):
        if not self.consumer_subscriptions:
            self.consumer_subscriptions = {
                "test_events": ConsumerSubscription(
                    topic=self.test_events_topic,
                    group_id=self.test_events_group_id,
                    dead_letter_topic=self.dead_letter_topic,
                ),
            }


def _to_runtime_config(base_config: BaseKafkaConfig) -> KafkaConfig:
    """把统一配置模型转换成 Kafka 模块运行时配置。"""
    return KafkaConfig(
        bootstrap_servers=list(base_config.bootstrap_servers),
        client_id=base_config.client_id,
        result_topic=base_config.result_topic,
        dead_letter_topic=base_config.dead_letter_topic,
        test_events_topic=base_config.test_events_topic,
        test_events_group_id=base_config.test_events_group_id,
        producer_options=base_config.producer_options.model_dump(),
        consumer_options=base_config.consumer_options.model_dump(),
    )


def load_kafka_config() -> KafkaConfig:
    """从已安装的 MongoDB 运行配置快照加载 Kafka 配置。"""
    return _to_runtime_config(get_settings().kafka)


__all__ = ["KafkaConfig", "ConsumerSubscription", "load_kafka_config"]

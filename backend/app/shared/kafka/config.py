"""Kafka 模块配置适配层。

Kafka 的真实配置来源只保留 `config.yaml`，本模块只负责把统一配置对象
转换为 Kafka runtime 需要的结构，并补充 consumer subscription 元数据。
"""

from dataclasses import dataclass, field
from typing import Any

from app.shared.config import KafkaConfig as BaseKafkaConfig
from app.shared.config import load_kafka_config as load_base_kafka_config


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

    该对象不再定义 Kafka 默认值，避免与 `app.shared.config.settings.KafkaConfig`
    形成第二套配置来源。所有字段都由 `config.yaml` 经统一 settings 加载后传入。
    """

    bootstrap_servers: list[str]
    client_id: str
    result_topic: str
    dead_letter_topic: str
    test_events_topic: str
    execution_result_group_id: str
    test_events_group_id: str
    producer_options: dict[str, Any]
    consumer_options: dict[str, Any]

    # Kafka consumer runner 需要的派生订阅配置，不作为独立配置源维护。
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


def _to_runtime_config(base_config: BaseKafkaConfig) -> KafkaConfig:
    """把统一配置模型转换成 Kafka 模块运行时配置。"""
    return KafkaConfig(
        bootstrap_servers=list(base_config.bootstrap_servers),
        client_id=base_config.client_id,
        result_topic=base_config.result_topic,
        dead_letter_topic=base_config.dead_letter_topic,
        test_events_topic=base_config.test_events_topic,
        execution_result_group_id=base_config.execution_result_group_id,
        test_events_group_id=base_config.test_events_group_id,
        producer_options=base_config.producer_options.model_dump(),
        consumer_options=base_config.consumer_options.model_dump(),
    )


def load_kafka_config() -> KafkaConfig:
    """从统一配置加载 Kafka 配置，并转换成 Kafka 模块运行时结构。"""
    return _to_runtime_config(load_base_kafka_config())


__all__ = ["KafkaConfig", "ConsumerSubscription", "load_kafka_config"]

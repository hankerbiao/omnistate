"""Kafka 模块配置。"""

import os
from dataclasses import dataclass, field
from typing import Any


DEFAULT_BOOTSTRAP_SERVERS = ["10.17.154.252:9092"]
DEFAULT_TASK_TOPIC = "dmlv4.tasks"
DEFAULT_RESULT_TOPIC = "dmlv4.results"
DEFAULT_DEAD_LETTER_TOPIC = "dmlv4.deadletter"
DEFAULT_EXECUTION_RESULT_GROUP_ID = "dmlv4-execution-result-consumers"
DEFAULT_TEST_EVENTS_TOPIC = "test-events"
DEFAULT_TEST_EVENTS_GROUP_ID = "dmlv4-test-events-consumers"


@dataclass(slots=True)
class ConsumerSubscription:
    """单个 consumer 订阅配置。"""

    topic: str
    group_id: str
    parser: str = "json"
    dead_letter_topic: str | None = DEFAULT_DEAD_LETTER_TOPIC


@dataclass(slots=True)
class KafkaConfig:
    """Kafka 运行时配置。"""

    bootstrap_servers: list[str] = field(default_factory=lambda: DEFAULT_BOOTSTRAP_SERVERS.copy())
    client_id: str = "dmlv4-shard"
    task_topic: str = DEFAULT_TASK_TOPIC
    result_topic: str = DEFAULT_RESULT_TOPIC
    dead_letter_topic: str = DEFAULT_DEAD_LETTER_TOPIC
    test_events_topic: str = DEFAULT_TEST_EVENTS_TOPIC
    consumer_subscriptions: dict[str, ConsumerSubscription] = field(default_factory=dict)
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


def _split_csv(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default.copy()
    return [item.strip() for item in value.split(",") if item.strip()]


def load_kafka_config() -> KafkaConfig:
    """从环境变量加载 Kafka 配置。"""
    task_topic = os.getenv("KAFKA_TASK_TOPIC", DEFAULT_TASK_TOPIC)
    result_topic = os.getenv("KAFKA_RESULT_TOPIC", DEFAULT_RESULT_TOPIC)
    dead_letter_topic = os.getenv("KAFKA_DEAD_LETTER_TOPIC", DEFAULT_DEAD_LETTER_TOPIC)
    test_events_topic = os.getenv("KAFKA_TEST_EVENTS_TOPIC", DEFAULT_TEST_EVENTS_TOPIC)
    return KafkaConfig(
        bootstrap_servers=_split_csv(
            os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
            DEFAULT_BOOTSTRAP_SERVERS,
        ),
        client_id=os.getenv("KAFKA_CLIENT_ID", "dmlv4-shard"),
        task_topic=task_topic,
        result_topic=result_topic,
        dead_letter_topic=dead_letter_topic,
        test_events_topic=test_events_topic,
        consumer_subscriptions={
            "execution_result": ConsumerSubscription(
                topic=result_topic,
                group_id=os.getenv(
                    "KAFKA_EXECUTION_RESULT_GROUP_ID",
                    DEFAULT_EXECUTION_RESULT_GROUP_ID,
                ),
                dead_letter_topic=dead_letter_topic,
            ),
            "test_events": ConsumerSubscription(
                topic=test_events_topic,
                group_id=os.getenv(
                    "KAFKA_TEST_EVENTS_GROUP_ID",
                    DEFAULT_TEST_EVENTS_GROUP_ID,
                ),
                dead_letter_topic=dead_letter_topic,
            ),
        },
    )

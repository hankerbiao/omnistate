"""Kafka 模块配置。"""

import os
from dataclasses import dataclass, field
from typing import Any


DEFAULT_BOOTSTRAP_SERVERS = ["10.17.154.252:9092"]
DEFAULT_TASK_TOPIC = "dmlv4.tasks"
DEFAULT_RESULT_TOPIC = "dmlv4.results"
DEFAULT_DEAD_LETTER_TOPIC = "dmlv4.deadletter"


@dataclass(slots=True)
class KafkaConfig:
    """Kafka 运行时配置。"""

    bootstrap_servers: list[str] = field(default_factory=lambda: DEFAULT_BOOTSTRAP_SERVERS.copy())
    client_id: str = "dmlv4-shard"
    task_topic: str = DEFAULT_TASK_TOPIC
    result_topic: str = DEFAULT_RESULT_TOPIC
    dead_letter_topic: str = DEFAULT_DEAD_LETTER_TOPIC
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
    return KafkaConfig(
        bootstrap_servers=_split_csv(
            os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
            DEFAULT_BOOTSTRAP_SERVERS,
        ),
        client_id=os.getenv("KAFKA_CLIENT_ID", "dmlv4-shard"),
        task_topic=os.getenv("KAFKA_TASK_TOPIC", DEFAULT_TASK_TOPIC),
        result_topic=os.getenv("KAFKA_RESULT_TOPIC", DEFAULT_RESULT_TOPIC),
        dead_letter_topic=os.getenv("KAFKA_DEAD_LETTER_TOPIC", DEFAULT_DEAD_LETTER_TOPIC),
    )

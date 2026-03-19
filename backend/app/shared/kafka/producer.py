"""Kafka producer runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError

from app.shared.core.logger import log
from app.shared.kafka.config import KafkaConfig, load_kafka_config


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


@dataclass(slots=True)
class TaskMessage:
    """任务消息数据结构。"""

    task_id: str
    task_type: str
    task_data: dict[str, Any]
    source: str = "dmlv4-system"
    priority: int = 1
    create_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "task_data": self.task_data,
            "source": self.source,
            "priority": self.priority,
            "create_time": self.create_time,
        }

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "TaskMessage":
        data = json.loads(json_str)
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            task_data=data["task_data"],
            source=data.get("source", "dmlv4-system"),
            priority=data.get("priority", 1),
            create_time=data.get("create_time", datetime.now(UTC).isoformat()),
        )


@dataclass(slots=True)
class ResultMessage:
    """结果消息数据结构。"""

    task_id: str
    status: str
    result_data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    executor: str = "unknown"
    complete_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "executor": self.executor,
            "complete_time": self.complete_time,
        }

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ResultMessage":
        data = json.loads(json_str)
        return cls(
            task_id=data["task_id"],
            status=data["status"],
            result_data=data.get("result_data") or {},
            error_message=data.get("error_message"),
            executor=data.get("executor", "unknown"),
            complete_time=data.get("complete_time", datetime.now(UTC).isoformat()),
        )


class KafkaProducerManager:
    """只负责 Kafka 生产者生命周期与消息发送。"""

    def __init__(
        self,
        bootstrap_servers: list[str] | None = None,
        client_id: str | None = None,
        config: KafkaConfig | None = None,
    ) -> None:
        runtime_config = config or load_kafka_config()
        if bootstrap_servers is not None:
            runtime_config.bootstrap_servers = bootstrap_servers
        if client_id is not None:
            runtime_config.client_id = client_id

        self.config = runtime_config
        self.bootstrap_servers = runtime_config.bootstrap_servers
        self.client_id = runtime_config.client_id
        self.task_topic = runtime_config.task_topic
        self.result_topic = runtime_config.result_topic
        self.dead_letter_topic = runtime_config.dead_letter_topic
        self.producer: KafkaProducer | None = None
        self.is_running = False

    def _create_producer(self) -> KafkaProducer:
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            value_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else v,
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            **self.config.producer_options,
        )

    def start(self) -> None:
        if self.is_running:
            return
        self.producer = self._create_producer()
        self.is_running = True
        log.info("Kafka producer manager started")

    def stop(self) -> None:
        if self.producer is not None:
            self.producer.close()
            self.producer = None
        self.is_running = False
        log.info("Kafka producer manager stopped")

    def _send_message(
        self,
        topic: str,
        key: str,
        value: str,
        headers: list[tuple[str, bytes]] | None = None,
    ) -> bool:
        if not self.is_running or self.producer is None:
            log.error("Kafka producer manager is not running")
            return False

        try:
            future = self.producer.send(topic=topic, key=key, value=value, headers=headers)
            future.get(timeout=10)
            return True
        except KafkaTimeoutError:
            log.error(f"Kafka send timeout, topic={topic}, key={key}")
            return False
        except KafkaError as exc:
            log.error(f"Kafka send failed, topic={topic}, key={key}, error={exc}")
            return False
        except Exception as exc:
            log.error(f"Kafka send failed, topic={topic}, key={key}, error={exc}")
            return False

    def send_task(self, task_message: TaskMessage, priority: int | None = None) -> bool:
        message_priority = task_message.priority if priority is None else priority
        success = self._send_message(
            topic=self.task_topic,
            key=task_message.task_id,
            value=task_message.to_json(),
            headers=[
                ("priority", str(message_priority).encode("utf-8")),
                ("task_type", task_message.task_type.encode("utf-8")),
                ("source", task_message.source.encode("utf-8")),
            ],
        )
        if success:
            log.info(f"Task sent to Kafka successfully: {task_message.task_id}")
        return success

    def send_result(self, result_message: ResultMessage) -> bool:
        return self._send_message(
            topic=self.result_topic,
            key=result_message.task_id,
            value=result_message.to_json(),
            headers=[
                ("status", result_message.status.encode("utf-8")),
                ("executor", result_message.executor.encode("utf-8")),
            ],
        )

    def send_dead_letter(
        self,
        message_key: str,
        payload: dict[str, Any],
        headers: list[tuple[str, bytes]] | None = None,
    ) -> bool:
        return self._send_message(
            topic=self.dead_letter_topic,
            key=message_key,
            value=_json_dumps(payload),
            headers=headers,
        )

    def health_check(self) -> dict[str, Any]:
        if not self.is_running:
            return {
                "component": "kafka_producer_manager",
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "STOPPED",
                "message": "Kafka producer manager is not running",
            }

        return {
            "component": "kafka_producer_manager",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "HEALTHY" if self.producer is not None else "DEGRADED",
            "message": "Kafka producer manager is operating normally",
            "details": {
                "bootstrap_servers": self.bootstrap_servers,
                "client_id": self.client_id,
                "producer_available": self.producer is not None,
                "topics": {
                    "task_topic": self.task_topic,
                    "result_topic": self.result_topic,
                    "dead_letter_topic": self.dead_letter_topic,
                },
            },
        }

    def __enter__(self) -> "KafkaProducerManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

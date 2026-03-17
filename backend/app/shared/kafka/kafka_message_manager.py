"""Kafka 消息管理器。"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, KafkaTimeoutError

from app.shared.core.logger import log
from app.shared.kafka.config import KafkaConfig, load_kafka_config

CONSUMER_GROUPS = {
    "task": "dmlv4-task-handlers",
    "result": "dmlv4-result-collectors",
    "deadletter": "dmlv4-dlq-handlers",
}


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


class KafkaMessageManager:
    """Kafka 消息管理类。"""

    def __init__(
            self,
            bootstrap_servers: list[str] | None = None,
            client_id: str | None = None,
            config: KafkaConfig | None = None,
    ):
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
        self.consumers: dict[str, KafkaConsumer] = {}
        self.task_handlers: dict[str, Callable] = {}
        self.is_running = False

    def _create_producer(self) -> KafkaProducer:
        try:
            return KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else v,
                key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
                **self.config.producer_options,
            )
        except Exception as e:
            log.error(f"创建 Kafka 生产者失败: {e}")
            raise

    def _create_consumer(self, group_id: str, topics: list[str]) -> KafkaConsumer:
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"{self.client_id}-{group_id}",
                group_id=group_id,
                value_deserializer=lambda m: m.decode("utf-8") if m else None,
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                **self.config.consumer_options,
            )
            consumer.subscribe(topics)
            return consumer
        except Exception as e:
            log.error(f"创建 Kafka 消费者失败: {e}")
            raise

    def _send_message(
            self,
            topic: str,
            key: str,
            value: str,
            headers: list[tuple[str, bytes]] | None = None,
    ) -> bool:
        if not self.is_running or not self.producer:
            log.error("消息管理器未启动或生产者不可用")
            return False

        try:
            future = self.producer.send(topic=topic, key=key, value=value, headers=headers)
            future.get(timeout=10)
            return True
        except KafkaTimeoutError:
            log.error(f"Kafka 发送超时, topic={topic}, key={key}")
            return False
        except KafkaError as e:
            log.error(f"Kafka 发送失败, topic={topic}, key={key}, error={e}")
            return False
        except Exception as e:
            log.error(f"发送消息失败, topic={topic}, key={key}, error={e}")
            return False

    def start(self) -> None:
        if self.is_running:
            return

        try:
            self.producer = self._create_producer()
            self.consumers["task"] = self._create_consumer(CONSUMER_GROUPS["task"], [self.task_topic])
            self.consumers["result"] = self._create_consumer(CONSUMER_GROUPS["result"], [self.result_topic])
            self.consumers["deadletter"] = self._create_consumer(
                CONSUMER_GROUPS["deadletter"],
                [self.dead_letter_topic],
            )
            self.is_running = True
            log.info("Kafka 消息管理器启动成功")
        except Exception as e:
            log.error(f"启动 Kafka 消息管理器失败: {e}")
            raise

    def stop(self) -> None:
        try:
            for name, consumer in self.consumers.items():
                consumer.close()
                log.info(f"关闭 {name} 消费者")
            self.consumers.clear()

            if self.producer:
                self.producer.close()
                log.info("关闭生产者")
                self.producer = None

            self.is_running = False
            log.info("Kafka 消息管理器已停止")
        except Exception as e:
            log.error(f"停止 Kafka 消息管理器时出错: {e}")

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
            log.info(f"任务发送成功 - ID: {task_message.task_id}, 类型: {task_message.task_type}")
        return success

    def health_check(self) -> dict[str, Any]:
        health_status: dict[str, Any] = {
            "component": "kafka_message_manager",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "UNKNOWN",
        }

        try:
            if not self.is_running:
                health_status["status"] = "STOPPED"
                health_status["message"] = "Kafka message manager is not running"
                return health_status

            if not self.producer:
                health_status["status"] = "DEGRADED"
                health_status["message"] = "Kafka producer is not available"
                return health_status

            if hasattr(self.producer, "_closed") and self.producer._closed:
                health_status["status"] = "DEGRADED"
                health_status["message"] = "Kafka producer appears to be closed"
                return health_status

            health_status["status"] = "HEALTHY"
            health_status["message"] = "Kafka message manager is operating normally"
            health_status["details"] = {
                "is_running": self.is_running,
                "bootstrap_servers": self.bootstrap_servers,
                "client_id": self.client_id,
                "producer_available": self.producer is not None,
                "consumer_count": len(self.consumers),
                "topics": {
                    "task_topic": self.task_topic,
                    "result_topic": self.result_topic,
                    "dead_letter_topic": self.dead_letter_topic,
                },
            }
        except Exception as e:
            health_status["status"] = "ERROR"
            health_status["message"] = f"Health check failed: {str(e)}"
            log.exception(f"Kafka health check error: {str(e)}")

        return health_status

    def __enter__(self) -> "KafkaMessageManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

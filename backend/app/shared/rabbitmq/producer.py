"""RabbitMQ producer runtime."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.shared.core.logger import log
from app.shared.kafka.producer import TaskMessage
from app.shared.rabbitmq.config import RabbitMQConfig, load_rabbitmq_config

try:
    import pika
    from pika.credentials import PlainCredentials
    from pika.exceptions import AMQPError
except ImportError:  # pragma: no cover - tested via runtime initialization path
    pika = None
    PlainCredentials = None
    AMQPError = Exception


class RabbitMQProducerManager:
    """只负责 RabbitMQ 生产者生命周期与消息发送。"""

    def __init__(self, config: RabbitMQConfig | None = None) -> None:
        self.config = config or load_rabbitmq_config()
        self.connection = None
        self.channel = None
        self.is_running = False

    def _create_connection(self):
        if pika is None or PlainCredentials is None:
            raise RuntimeError("pika is required to use RabbitMQ dispatch")

        parameters = pika.ConnectionParameters(
            host=self.config.host,
            port=self.config.port,
            virtual_host=self.config.virtual_host,
            credentials=PlainCredentials(
                username=self.config.username,
                password=self.config.password,
            ),
            heartbeat=self.config.heartbeat,
            blocked_connection_timeout=self.config.blocked_connection_timeout,
            connection_attempts=self.config.connection_attempts,
            retry_delay=self.config.retry_delay,
            ssl_options=self.config.ssl_options,
        )
        return pika.BlockingConnection(parameters)

    def start(self) -> None:
        if self._is_connection_ready():
            return
        self.connection = self._create_connection()
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.config.task_queue, durable=True)
        self.is_running = True
        log.info("RabbitMQ producer manager started")

    def stop(self) -> None:
        if self.channel is not None:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None
        if self.connection is not None:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
        self.is_running = False
        log.info("RabbitMQ producer manager stopped")

    def _is_connection_ready(self) -> bool:
        return (
            self.is_running
            and self.connection is not None
            and self.channel is not None
            and getattr(self.connection, "is_open", True)
            and getattr(self.channel, "is_open", True)
        )

    def _ensure_connection_ready(self) -> bool:
        if self._is_connection_ready():
            return True
        try:
            self.stop()
            self.start()
            return self._is_connection_ready()
        except Exception as exc:
            log.error(f"Failed to recover RabbitMQ producer manager: {exc}")
            return False

    def send_task(self, task_message: TaskMessage, priority: int | None = None) -> bool:
        if not self._ensure_connection_ready():
            log.error("RabbitMQ producer manager is not running")
            return False

        message_priority = task_message.priority if priority is None else priority
        properties = None
        if pika is not None:
            properties = pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                content_encoding="utf-8",
                priority=message_priority,
                headers={
                    "task_type": task_message.task_type,
                    "source": task_message.source,
                },
                message_id=task_message.task_id,
                timestamp=int(datetime.now(UTC).timestamp()),
            )

        try:
            self.channel.basic_publish(
                exchange=self.config.task_exchange,
                routing_key=self.config.task_routing_key,
                body=json.dumps(
                    task_message.task_data,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8"),
                properties=properties,
                mandatory=False,
            )
            log.info(f"Task sent to RabbitMQ successfully: {task_message.task_id}")
            return True
        except AMQPError as exc:
            log.error(f"RabbitMQ send failed, task_id={task_message.task_id}, error={exc}")
            return False
        except Exception as exc:
            log.error(f"RabbitMQ send failed, task_id={task_message.task_id}, error={exc}")
            return False

    def health_check(self) -> dict[str, Any]:
        if not self.is_running:
            return {
                "component": "rabbitmq_producer_manager",
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "STOPPED",
                "message": "RabbitMQ producer manager is not running",
            }

        return {
            "component": "rabbitmq_producer_manager",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "HEALTHY" if self._is_connection_ready() else "DEGRADED",
            "message": "RabbitMQ producer manager is operating normally",
            "details": {
                "host": self.config.host,
                "port": self.config.port,
                "virtual_host": self.config.virtual_host,
                "task_queue": self.config.task_queue,
                "task_exchange": self.config.task_exchange,
                "task_routing_key": self.config.task_routing_key,
                "channel_available": self.channel is not None,
                "channel_open": getattr(self.channel, "is_open", False),
                "connection_open": getattr(self.connection, "is_open", False),
            },
        }

    def __enter__(self) -> "RabbitMQProducerManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

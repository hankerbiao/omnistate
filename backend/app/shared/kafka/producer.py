"""Kafka producer runtime.

该模块封装 DML V4 后端向 Kafka 写入消息的运行时能力，主要负责：
- 定义任务消息与结果消息的统一 JSON 结构。
- 管理 KafkaProducer 的创建、启动、关闭与健康检查。
- 向结果主题和死信主题发送消息。

注意：这里不承载业务状态流转逻辑，只负责生产端的消息格式与发送可靠性。
"""

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
    """将消息体序列化为紧凑 JSON 字符串，并保留中文字符。"""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


@dataclass(slots=True)
class TaskMessage:
    """任务消息数据结构。

    用于描述要投递给异步执行端的任务。字段会直接序列化到 Kafka 消息体，
    因此新增或调整字段时需要同步检查消费者解析逻辑。
    """

    # 业务任务的唯一标识，通常也作为 Kafka 消息 key，便于按任务维度追踪。
    task_id: str
    # 任务类型，用于消费者路由到不同的执行逻辑。
    task_type: str
    # 任务执行所需的业务参数，保持 dict 结构以兼容不同任务类型。
    task_data: dict[str, Any]
    # 消息来源，便于排查跨系统调用链路。
    source: str = "dmlv4-system"
    # 任务优先级，数值含义由消费者侧调度策略解释。
    priority: int = 1
    # 创建时间使用 UTC ISO 格式，避免跨时区服务之间产生歧义。
    create_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """转换为可 JSON 序列化的字典结构。"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "task_data": self.task_data,
            "source": self.source,
            "priority": self.priority,
            "create_time": self.create_time,
        }

    def to_json(self) -> str:
        """转换为 Kafka 消息体使用的 JSON 字符串。"""
        return _json_dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "TaskMessage":
        """从 Kafka 消息体反序列化为任务消息对象。"""
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
    """结果消息数据结构。

    用于执行端回传任务处理结果。结果消息通常写入结果主题，
    后续由业务服务或监听器消费并更新任务状态。
    """

    # 对应 TaskMessage.task_id，用于把执行结果关联回原始任务。
    task_id: str
    # 执行状态，例如 SUCCESS、FAILED 等，具体枚举由上层业务约定。
    status: str
    # 执行成功或部分成功时返回的结构化数据。
    result_data: dict[str, Any] = field(default_factory=dict)
    # 执行失败时的错误说明；成功时通常为空。
    error_message: str | None = None
    # 执行器标识，便于定位是哪一个 worker 或服务实例处理了任务。
    executor: str = "unknown"
    # 完成时间使用 UTC ISO 格式，便于和 create_time 做耗时计算。
    complete_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """转换为可 JSON 序列化的字典结构。"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "executor": self.executor,
            "complete_time": self.complete_time,
        }

    def to_json(self) -> str:
        """转换为 Kafka 消息体使用的 JSON 字符串。"""
        return _json_dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ResultMessage":
        """从 Kafka 消息体反序列化为结果消息对象。"""
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
    """只负责 Kafka 生产者生命周期与消息发送。

    该类刻意保持职责单一：
    - 读取并持有 Kafka 生产者配置。
    - 延迟创建 KafkaProducer，避免模块导入时直接连接外部服务。
    - 统一处理发送成功、超时和异常日志。
    """

    def __init__(
        self,
        bootstrap_servers: list[str] | None = None,
        client_id: str | None = None,
        config: KafkaConfig | None = None,
    ) -> None:
        # 允许测试或本地调试通过参数覆盖配置文件中的连接信息。
        runtime_config = config or load_kafka_config()
        if bootstrap_servers is not None:
            runtime_config.bootstrap_servers = bootstrap_servers
        if client_id is not None:
            runtime_config.client_id = client_id

        self.config = runtime_config
        self.bootstrap_servers = runtime_config.bootstrap_servers
        self.client_id = runtime_config.client_id
        self.result_topic = runtime_config.result_topic
        self.dead_letter_topic = runtime_config.dead_letter_topic
        self.producer: KafkaProducer | None = None
        self.is_running = False

    def _create_producer(self) -> KafkaProducer:
        """按当前运行时配置创建 KafkaProducer 实例。"""
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            value_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else v,
            key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
            **self.config.producer_options,
        )

    def start(self) -> None:
        """启动生产者管理器，并建立 KafkaProducer 实例。"""
        if self.is_running:
            return
        self.producer = self._create_producer()
        self.is_running = True
        log.info("Kafka producer manager started")

    def stop(self) -> None:
        """关闭 KafkaProducer，释放网络连接等底层资源。"""
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
        """向指定主题发送消息。

        发送采用同步等待确认的方式：send 返回 future 后调用 get(timeout=10)。
        这样调用方可以根据 bool 返回值判断消息是否已经被 Kafka 客户端确认。
        """
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

    def send_result(self, result_message: ResultMessage) -> bool:
        """发送任务执行结果消息到结果主题。"""
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
        """发送无法正常处理的消息到死信主题。

        死信主题用于保存失败消息的原始上下文，方便后续人工排查或补偿重试。
        """
        return self._send_message(
            topic=self.dead_letter_topic,
            key=message_key,
            value=_json_dumps(payload),
            headers=headers,
        )

    def health_check(self) -> dict[str, Any]:
        """返回生产者管理器的健康状态信息。"""
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
                    "result_topic": self.result_topic,
                    "dead_letter_topic": self.dead_letter_topic,
                },
            },
        }

    def __enter__(self) -> "KafkaProducerManager":
        """支持 with 语句自动启动生产者。"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """支持 with 语句退出时自动关闭生产者。"""
        self.stop()

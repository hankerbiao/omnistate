#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock RabbitMQ Consumer - RabbitMQ 消费端调试脚本

用途：
    该脚本用于消费 dmlv4 RabbitMQ 任务队列中的消息，模拟执行后将结果和
    测试事件回写到 Kafka，便于联调 RabbitMQ -> 执行端 -> Kafka 回报链路。

使用方式：
    python scripts/mock_rabbitmq_consumer.py
"""

from __future__ import annotations

import importlib
import json
import os
import socket
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from app.shared.kafka.config import load_kafka_config
from app.shared.kafka.producer import TaskMessage
from app.shared.rabbitmq.config import load_rabbitmq_config


DEFAULT_EXECUTOR = "mock-rabbitmq-consumer"
DEFAULT_EVENT_SCHEMA = "mock-test-event@1"
DEFAULT_CASE_DELAY_SEC = 0.2
DEFAULT_PLATFORM_URL = "http://127.0.0.1:8000"
DEFAULT_AGENT_ID = "mock-rabbitmq-agent"
DEFAULT_AGENT_HOST = "127.0.0.1"
DEFAULT_AGENT_PORT = 19091
DEFAULT_AGENT_REGION = "default"
DEFAULT_HEARTBEAT_INTERVAL = 30
DEFAULT_HEARTBEAT_TTL = 90


def pretty_json(data: dict[str, Any]) -> str:
    """格式化 JSON 输出。"""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def _load_pika():
    """延迟导入 pika，避免模块导入阶段被旧版本适配器拖垮。"""
    try:
        pika_module = importlib.import_module("pika")
        credentials_module = importlib.import_module("pika.credentials")
        return pika_module, credentials_module.PlainCredentials
    except Exception as exc:  # pragma: no cover - exact import error depends on runtime
        raise RuntimeError(
            "pika is required and must be compatible with Python 3.13+ "
            "to run mock_rabbitmq_consumer.py"
        ) from exc


def _load_kafka_producer_class():
    """延迟导入 KafkaProducer，避免脚本加载时强依赖外部运行环境。"""
    try:
        kafka_module = importlib.import_module("kafka")
        return kafka_module.KafkaProducer
    except Exception as exc:  # pragma: no cover - exact import error depends on runtime
        raise RuntimeError(
            "kafka-python is required to run mock_rabbitmq_consumer.py"
        ) from exc


def _load_requests_module():
    """延迟导入 requests，避免脚本加载时强依赖外部运行环境。"""
    try:
        return importlib.import_module("requests")
    except Exception as exc:  # pragma: no cover - exact import error depends on runtime
        raise RuntimeError(
            "requests is required to run mock_rabbitmq_consumer.py"
        ) from exc


def detect_local_ip() -> str:
    """探测本机对外可见 IP。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def resolve_runtime_config() -> dict[str, Any]:
    """使用共享默认配置。"""
    rabbitmq_config = load_rabbitmq_config()
    kafka_config = load_kafka_config()
    return {
        "rabbitmq": {
            "host": rabbitmq_config.host,
            "port": rabbitmq_config.port,
            "username": rabbitmq_config.username,
            "password": rabbitmq_config.password,
            "virtual_host": rabbitmq_config.virtual_host,
            "queue": rabbitmq_config.task_queue,
            "heartbeat": rabbitmq_config.heartbeat,
            "blocked_connection_timeout": rabbitmq_config.blocked_connection_timeout,
            "connection_attempts": rabbitmq_config.connection_attempts,
            "retry_delay": rabbitmq_config.retry_delay,
        },
        "kafka": {
            "bootstrap_servers": kafka_config.bootstrap_servers,
            "result_topic": kafka_config.result_topic,
            "test_events_topic": kafka_config.test_events_topic,
        },
        "platform": {
            "url": os.getenv("MOCK_PLATFORM_URL", DEFAULT_PLATFORM_URL).rstrip("/"),
            "agent_id": os.getenv("MOCK_AGENT_ID", DEFAULT_AGENT_ID),
            "host": os.getenv("MOCK_AGENT_HOST", DEFAULT_AGENT_HOST),
            "port": int(os.getenv("MOCK_AGENT_PORT", str(DEFAULT_AGENT_PORT))),
            "region": os.getenv("MOCK_AGENT_REGION", DEFAULT_AGENT_REGION),
            "heartbeat_interval": int(
                os.getenv("MOCK_HEARTBEAT_INTERVAL", str(DEFAULT_HEARTBEAT_INTERVAL))
            ),
            "heartbeat_ttl": int(os.getenv("MOCK_HEARTBEAT_TTL", str(DEFAULT_HEARTBEAT_TTL))),
        },
    }


def build_connection_parameters(runtime_config: dict[str, Any]):
    """构建 RabbitMQ 连接参数。"""
    pika, plain_credentials = _load_pika()
    rabbitmq_config = runtime_config["rabbitmq"]
    return pika.ConnectionParameters(
        host=rabbitmq_config["host"],
        port=rabbitmq_config["port"],
        virtual_host=rabbitmq_config["virtual_host"],
        credentials=plain_credentials(
            username=rabbitmq_config["username"],
            password=rabbitmq_config["password"],
        ),
        heartbeat=rabbitmq_config["heartbeat"],
        blocked_connection_timeout=rabbitmq_config["blocked_connection_timeout"],
        connection_attempts=rabbitmq_config["connection_attempts"],
        retry_delay=rabbitmq_config["retry_delay"],
    )


def create_kafka_producer(runtime_config: dict[str, Any]):
    """创建 Kafka 生产者，用于发送结果消息和测试事件。"""
    kafka_producer_cls = _load_kafka_producer_class()
    kafka_config = runtime_config["kafka"]
    return kafka_producer_cls(
        bootstrap_servers=kafka_config["bootstrap_servers"],
        value_serializer=lambda value: json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
    )


def decode_task_message(body: bytes) -> TaskMessage:
    """将 RabbitMQ 消息体解析为 TaskMessage。"""
    return TaskMessage.from_json(body.decode("utf-8"))


def build_test_event(
    task_id: str,
    phase: str,
    status: str,
    case_count: int,
    started_cases: int,
    finished_cases: int,
    failed_cases: int,
    case_id: str | None = None,
    case_title: str | None = None,
) -> dict[str, Any]:
    """构建 mock 测试事件。"""
    event = {
        "schema": DEFAULT_EVENT_SCHEMA,
        "event_id": str(uuid.uuid4()),
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "progress",
        "phase": phase,
        "status": status,
        "total_cases": case_count,
        "started_cases": started_cases,
        "finished_cases": finished_cases,
        "failed_cases": failed_cases,
    }
    if case_id:
        event["case_id"] = case_id
    if case_title:
        event["case_title"] = case_title
    return event


def build_result_message(task_id: str, duration: float, case_count: int) -> dict[str, Any]:
    """构建 mock 执行结果。"""
    return {
        "task_id": task_id,
        "status": "success",
        "result_data": {
            "duration": round(duration, 2),
            "summary": f"{case_count} passed",
        },
        "executor": DEFAULT_EXECUTOR,
        "complete_time": datetime.now(timezone.utc).isoformat(),
    }


class JsonHttpClient:
    """简单 JSON HTTP 客户端。"""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._requests = _load_requests_module()

    def post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


class ExecutionAgentClient:
    """负责向平台注册地址和定期发送心跳。"""

    def __init__(self, runtime_config: dict[str, Any]) -> None:
        platform_config = runtime_config["platform"]
        self.platform_url = platform_config["url"]
        self.agent_id = platform_config["agent_id"]
        self.host = platform_config["host"]
        self.port = platform_config["port"]
        self.region = platform_config["region"]
        self.heartbeat_interval = platform_config["heartbeat_interval"]
        self.heartbeat_ttl = platform_config["heartbeat_ttl"]
        self.base_url = f"http://{self.host}:{self.port}"
        self.http = JsonHttpClient()

    def build_register_payload(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "hostname": socket.gethostname(),
            "ip": detect_local_ip(),
            "port": self.port,
            "base_url": self.base_url,
            "region": self.region,
            "status": "ONLINE",
            "heartbeat_ttl_seconds": self.heartbeat_ttl,
        }

    def register_agent(self) -> dict[str, Any]:
        return self.http.post(
            f"{self.platform_url}/api/v1/execution/agents/register",
            self.build_register_payload(),
        )

    def send_heartbeat(self, status: str = "ONLINE") -> dict[str, Any]:
        return self.http.post(
            f"{self.platform_url}/api/v1/execution/agents/{self.agent_id}/heartbeat",
            {"status": status},
        )


def heartbeat_loop(agent_client: ExecutionAgentClient, stop_event: threading.Event) -> None:
    """后台定时发送心跳。"""
    while not stop_event.wait(agent_client.heartbeat_interval):
        try:
            agent_client.send_heartbeat(status="ONLINE")
            print(f"[-] sent agent heartbeat: agent_id={agent_client.agent_id}, status=ONLINE")
            sys.stdout.flush()
        except Exception as exc:
            print(f"[!] failed to send agent heartbeat: agent_id={agent_client.agent_id}, error={exc}")
            sys.stdout.flush()


class MockRabbitMQRuntime:
    """统一处理 RabbitMQ 输入和 Kafka 输出。"""

    def __init__(self, producer: Any, runtime_config: dict[str, Any]) -> None:
        self.producer = producer
        self.result_topic = runtime_config["kafka"]["result_topic"]
        self.test_events_topic = runtime_config["kafka"]["test_events_topic"]

    def process_task_message(
        self,
        task_message: TaskMessage,
        source_meta: dict[str, Any] | None = None,
    ) -> None:
        """处理任务消息，模拟执行并回写 Kafka。"""
        payload = task_message.task_data or {}
        cases = [case for case in payload.get("cases", []) if isinstance(case, dict) and case.get("case_id")]
        case_count = len(cases)
        task_id = task_message.task_id

        print("=" * 80)
        print("Received RabbitMQ task")
        print(
            f"task_id={task_id}, task_type={task_message.task_type}, "
            f"source={task_message.source}, priority={task_message.priority}, "
            f"case_count={case_count}"
        )
        if source_meta:
            print("source_meta:")
            print(pretty_json(source_meta))
        print("task_wrapper:")
        print(pretty_json(task_message.to_dict()))
        sys.stdout.flush()

        if case_count == 0:
            print(f"[!] task {task_id} has no executable cases, skip Kafka callbacks")
            sys.stdout.flush()
            return

        total_delay = 0.0
        finished_cases = 0
        failed_cases = 0

        for index, case_item in enumerate(cases, start=1):
            case_id = case_item["case_id"]
            case_title = case_item.get("script_name") or case_id
            case_start_event = build_test_event(
                task_id=task_id,
                phase="case_start",
                status="RUNNING",
                case_count=case_count,
                started_cases=index,
                finished_cases=finished_cases,
                failed_cases=failed_cases,
                case_id=case_id,
                case_title=case_title,
            )
            self.producer.send(self.test_events_topic, case_start_event)
            print(f"[-] sent case_start event: case_id={case_id}")
            print(pretty_json(case_start_event))

            time.sleep(DEFAULT_CASE_DELAY_SEC)
            total_delay += DEFAULT_CASE_DELAY_SEC
            finished_cases += 1

            case_finish_event = build_test_event(
                task_id=task_id,
                phase="case_finish",
                status="PASSED",
                case_count=case_count,
                started_cases=index,
                finished_cases=finished_cases,
                failed_cases=failed_cases,
                case_id=case_id,
                case_title=case_title,
            )
            self.producer.send(self.test_events_topic, case_finish_event)
            print(f"[-] sent case_finish event: case_id={case_id}")
            print(pretty_json(case_finish_event))

        task_finish_event = build_test_event(
            task_id=task_id,
            phase="task_finish",
            status="PASSED",
            case_count=case_count,
            started_cases=case_count,
            finished_cases=finished_cases,
            failed_cases=failed_cases,
        )
        self.producer.send(self.test_events_topic, task_finish_event)
        print("[-] sent task_finish event")
        print(pretty_json(task_finish_event))

        result_message = build_result_message(task_id, total_delay, case_count)
        self.producer.send(self.result_topic, result_message)
        print("[-] sent result message")
        print(pretty_json(result_message))
        sys.stdout.flush()


def start_consumer(runtime_config: dict[str, Any]) -> None:
    """启动消费循环。"""
    pika, _ = _load_pika()
    producer = create_kafka_producer(runtime_config)
    runtime = MockRabbitMQRuntime(producer=producer, runtime_config=runtime_config)
    agent_client = ExecutionAgentClient(runtime_config)
    heartbeat_stop_event = threading.Event()
    heartbeat_thread: threading.Thread | None = None

    parameters = build_connection_parameters(runtime_config)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=runtime_config["rabbitmq"]["queue"], durable=True)
    channel.basic_qos(prefetch_count=1)

    def _on_message(ch, method, properties, body) -> None:
        del properties
        try:
            task_message = decode_task_message(body)
            runtime.process_task_message(
                task_message,
                source_meta={
                    "delivery_tag": method.delivery_tag,
                    "routing_key": getattr(method, "routing_key", ""),
                    "exchange": getattr(method, "exchange", ""),
                },
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            print(f"[!] failed to process RabbitMQ message: {exc}")
            print(traceback.format_exc())
            if hasattr(ch, "basic_nack"):
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            else:
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            sys.stdout.flush()

    print(
        "[*] RabbitMQ mock consumer started: "
        f"{runtime_config['rabbitmq']['host']}:{runtime_config['rabbitmq']['port']} "
        f"queue={runtime_config['rabbitmq']['queue']}"
    )
    print(
        "[*] Kafka callbacks: "
        f"bootstrap_servers={','.join(runtime_config['kafka']['bootstrap_servers'])}, "
        f"result_topic={runtime.result_topic}, test_events_topic={runtime.test_events_topic}"
    )
    print(
        "[*] Execution agent registration: "
        f"platform_url={runtime_config['platform']['url']}, agent_id={agent_client.agent_id}, "
        f"heartbeat_interval={agent_client.heartbeat_interval}s"
    )
    print("[*] Press Ctrl+C to stop")
    sys.stdout.flush()

    register_response = agent_client.register_agent()
    print(f"[*] registered execution agent: agent_id={agent_client.agent_id}")
    print(pretty_json(register_response))
    agent_client.send_heartbeat(status="ONLINE")
    heartbeat_thread = threading.Thread(
        target=heartbeat_loop,
        args=(agent_client, heartbeat_stop_event),
        name="mock-rabbitmq-heartbeat",
        daemon=True,
    )
    heartbeat_thread.start()

    channel.basic_consume(
        queue=runtime_config["rabbitmq"]["queue"],
        on_message_callback=_on_message,
        auto_ack=False,
    )

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[*] Stopping RabbitMQ mock consumer...")
        sys.stdout.flush()
    finally:
        heartbeat_stop_event.set()
        if heartbeat_thread is not None and heartbeat_thread.is_alive():
            heartbeat_thread.join(timeout=2)
        try:
            agent_client.send_heartbeat(status="OFFLINE")
            print(f"[*] sent final agent heartbeat: agent_id={agent_client.agent_id}, status=OFFLINE")
            sys.stdout.flush()
        except Exception as exc:
            print(f"[!] failed to send final OFFLINE heartbeat: agent_id={agent_client.agent_id}, error={exc}")
            sys.stdout.flush()
        try:
            producer.flush()
        except Exception:
            pass
        try:
            producer.close()
        except Exception:
            pass
        if channel.is_open:
            channel.close()
        if connection.is_open:
            connection.close()


def main() -> None:
    """脚本入口。"""
    runtime_config = resolve_runtime_config()
    start_consumer(runtime_config)


if __name__ == "__main__":
    main()

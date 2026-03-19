#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Test Framework Client - 模拟测试框架执行器

用途：
    该脚本模拟一个测试框架执行器，用于与 dmlv4 后端系统进行联调测试。
    它从 Kafka 的 dmlv4.tasks topic 消费任务，模拟执行后返回 mock 结果和测试事件。

功能：
    1. 消费 dmlv4.tasks topic 中的任务消息
    2. 解析任务中的真实 case 列表
    3. 模拟任务执行（随机延迟）
    4. 发送执行结果到 dmlv4.results topic
    5. 发送测试事件到 test-events topic（progress/case_start/case_finish/task_finish）

使用方式：
    # 基本用法
    python scripts/mock_test_framework.py

    # 自定义参数
    python scripts/mock_test_framework.py --delay-min 1 --delay-max 3 --case-count 3

    # 使用环境变量
    export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    python scripts/mock_test_framework.py

依赖：
    pip install kafka-python
"""

import argparse
import json
import os
import signal
import socket
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

import requests
from kafka import KafkaConsumer, KafkaProducer


# ============================================================
# 默认配置常量
# ============================================================

# Kafka 连接地址
DEFAULT_BOOTSTRAP_SERVERS = "10.17.154.252:9092"

# Kafka Topic 名称
DEFAULT_TASK_TOPIC = "dmlv4.tasks"          # 任务输入 topic
DEFAULT_RESULT_TOPIC = "dmlv4.results"       # 结果输出 topic
DEFAULT_TEST_EVENTS_TOPIC = "test-events"   # 测试事件 topic

# Consumer Group ID
DEFAULT_GROUP_ID = "dmlv4-mock-executor"
DEFAULT_PLATFORM_URL = "http://127.0.0.1:8000"
DEFAULT_AGENT_ID = "mock-framework-agent"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 19090
DEFAULT_REGION = "default"
DEFAULT_HEARTBEAT_INTERVAL = 30
DEFAULT_HEARTBEAT_TTL = 90

# 执行延迟配置（秒）
DEFAULT_DELAY_MIN = 0.5   # 最小延迟
DEFAULT_DELAY_MAX = 2.0   # 最大延迟


def pretty_json(data: dict[str, Any]) -> str:
    """格式化 JSON 输出，方便终端调试。"""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def summarize_case(case_item: dict[str, Any], index: int, total: int) -> str:
    """生成单条 case 的调试摘要。"""
    case_id = case_item.get("case_id", "unknown-case")
    auto_case_id = case_item.get("auto_case_id", "-")
    title = case_item.get("case_title") or case_item.get("title") or "-"
    return f"[{index}/{total}] case_id={case_id}, auto_case_id={auto_case_id}, title={title}"


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


def parse_args():
    """
    解析命令行参数。

    返回:
        argparse.Namespace: 解析后的命令行参数对象
    """
    parser = argparse.ArgumentParser(
        description="Mock Test Framework Client - 模拟测试框架执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/mock_test_framework.py
  python scripts/mock_test_framework.py --delay-min 1 --delay-max 3 --case-count 3
  python scripts/mock_test_framework.py --bootstrap-servers localhost:9092 --group-id my-group
        """
    )

    # Kafka 配置
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", DEFAULT_BOOTSTRAP_SERVERS),
        help="Kafka bootstrap servers 地址，多个地址用逗号分隔 (default: %(default)s)",
    )
    parser.add_argument(
        "--group-id",
        default=DEFAULT_GROUP_ID,
        help="Consumer group ID (default: %(default)s)",
    )
    parser.add_argument(
        "--platform-url",
        default=os.getenv("MOCK_PLATFORM_URL", DEFAULT_PLATFORM_URL),
        help="平台 API 地址 (default: %(default)s)",
    )
    parser.add_argument(
        "--agent-id",
        default=os.getenv("MOCK_AGENT_ID", DEFAULT_AGENT_ID),
        help="执行代理 ID (default: %(default)s)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MOCK_AGENT_HOST", DEFAULT_HOST),
        help="代理对外主机地址 (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MOCK_AGENT_PORT", str(DEFAULT_PORT))),
        help="代理端口 (default: %(default)s)",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("MOCK_AGENT_REGION", DEFAULT_REGION),
        help="代理所属区域 (default: %(default)s)",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=int(os.getenv("MOCK_HEARTBEAT_INTERVAL", str(DEFAULT_HEARTBEAT_INTERVAL))),
        help="心跳间隔秒数 (default: %(default)s)",
    )
    parser.add_argument(
        "--heartbeat-ttl",
        type=int,
        default=int(os.getenv("MOCK_HEARTBEAT_TTL", str(DEFAULT_HEARTBEAT_TTL))),
        help="心跳 TTL 秒数 (default: %(default)s)",
    )

    # 执行配置
    parser.add_argument(
        "--delay-min",
        type=float,
        default=DEFAULT_DELAY_MIN,
        help="最小执行延迟时间，单位秒 (default: %(default)s)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=DEFAULT_DELAY_MAX,
        help="最大执行延迟时间，单位秒 (default: %(default)s)",
    )
    return parser.parse_args()


class JsonHttpClient:
    """简单 JSON HTTP 客户端。"""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


class FrameworkClient:
    """负责向平台注册代理并定期发送心跳。"""

    def __init__(
        self,
        platform_url: str,
        agent_id: str,
        host: str,
        port: int,
        region: str,
        heartbeat_interval: int,
        heartbeat_ttl_seconds: int,
    ) -> None:
        self.platform_url = platform_url.rstrip("/")
        self.agent_id = agent_id
        self.host = host
        self.port = port
        self.region = region
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_ttl_seconds = heartbeat_ttl_seconds
        self.base_url = f"http://{host}:{port}"
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
            "heartbeat_ttl_seconds": self.heartbeat_ttl_seconds,
        }

    def register_agent(self) -> None:
        payload = self.build_register_payload()
        url = f"{self.platform_url}/api/v1/execution/agents/register"
        self.http.post(url, payload)

    def send_heartbeat(self) -> dict[str, Any]:
        url = f"{self.platform_url}/api/v1/execution/agents/{self.agent_id}/heartbeat"
        payload = {"status": "ONLINE"}
        return self.http.post(url, payload)


def heartbeat_loop(client: FrameworkClient, stop_event: threading.Event) -> None:
    """后台定时发送心跳。"""
    while not stop_event.wait(client.heartbeat_interval):
        try:
            client.send_heartbeat()
        except Exception:
            pass  # 心跳失败静默处理


def create_consumer(bootstrap_servers: str, group_id: str) -> KafkaConsumer:
    """
    创建 Kafka 消费者。

    订阅 dmlv4.tasks topic，用于接收任务消息。

    参数:
        bootstrap_servers: Kafka 服务器地址
        group_id: Consumer group ID

    返回:
        KafkaConsumer: 配置好的 Kafka 消费者实例
    """
    return KafkaConsumer(
        DEFAULT_TASK_TOPIC,  # 订阅的任务 topic
        bootstrap_servers=bootstrap_servers.split(","),
        group_id=group_id,
        # 自动将消息值从 JSON 字符串反序列化为 Python 字典
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        # 从最早的消息开始消费
        auto_offset_reset="earliest",
        # 自动提交消费位移
        enable_auto_commit=True,
    )


def create_producer(bootstrap_servers: str) -> KafkaProducer:
    """
    创建 Kafka 生产者。

    用于发送结果消息和测试事件到对应的 topic。

    参数:
        bootstrap_servers: Kafka 服务器地址

    返回:
        KafkaProducer: 配置好的 Kafka 生产者实例
    """
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        # 自动将 Python 字典序列化为 JSON 字符串
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )


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
    """
    构建测试事件消息。

    测试事件遵循当前 execution 模块消费规则，需要包含以下关键字段：
    - schema: 必须以 "-test-event@1" 结尾
    - event_id: 唯一事件 ID
    - task_id: 关联的任务 ID
    - timestamp: 事件时间戳
    - event_type: 固定为 progress
    - phase: case_start / case_finish / task_finish
    - status: RUNNING / PASSED / FAILED

    参数:
        task_id: 任务 ID
        phase: 事件阶段
        status: 状态
        case_count: 总测试用例数
        started_cases: 已开始用例数
        finished_cases: 已完成用例数
        failed_cases: 已失败用例数
        case_id: 测试用例 ID
        case_title: 测试用例标题

    返回:
        dict: 测试事件字典，可直接序列化为 JSON 发送到 Kafka
    """
    # 获取当前时间（UTC 时区）
    now = datetime.now(timezone.utc)

    # 基础事件结构
    event = {
        "schema": "mock-test-event@1",
        "event_id": str(uuid.uuid4()),
        "task_id": task_id,
        "timestamp": now.isoformat(),
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
    """
    构建任务结果消息。

    结果消息遵循 ResultMessage schema，包含任务执行结果信息。

    参数:
        task_id: 任务 ID
        duration: 执行耗时（秒）
        case_count: 通过的测试用例数

    返回:
        dict: 结果消息字典，可直接序列化为 JSON 发送到 Kafka
    """
    return {
        "task_id": task_id,                           # 任务 ID
        "status": "success",                          # 执行状态
        "result_data": {
            "duration": round(duration, 2),           # 执行耗时
            "summary": f"{case_count} passed",        # 结果摘要
        },
        "executor": "mock-executor",                  # 执行器标识
        "complete_time": datetime.now(timezone.utc).isoformat(),  # 完成时间
    }


def simulate_execution(
    consumer: KafkaConsumer,
    producer: KafkaProducer,
    delay_min: float,
    delay_max: float,
) -> None:
    """
    模拟任务执行的主循环。

    持续从 Kafka 消费任务，处理后发送结果和事件。
    此函数会阻塞直到收到中断信号。

    参数:
        consumer: Kafka 消费者实例
        producer: Kafka 生产者实例
        delay_min: 最小执行延迟
        delay_max: 最大执行延迟
    """
    import random

    print(f"[*] Mock Test Framework Client 已启动")
    print(f"[*] 监听 Topic: {DEFAULT_TASK_TOPIC}")
    print(f"[*] 输出 Topic: result={DEFAULT_RESULT_TOPIC}, test_events={DEFAULT_TEST_EVENTS_TOPIC}")
    print(f"[*] 执行延迟范围: {delay_min}-{delay_max}秒, 按任务真实 case 列表执行")
    print(f"[*] 按 Ctrl+C 退出\n")

    while True:
        try:
            # 拉取消息（超时 1 秒）
            records = consumer.poll(timeout_ms=1000)

            # 处理每个消息
            for topic_partition, messages in records.items():
                for message in messages:
                    # 解析任务数据
                    task_data = message.value
                    task_id = task_data.get("task_id", "unknown")
                    task_type = task_data.get("task_type", "unknown")
                    payload = task_data.get("task_data", {}) or {}
                    external_task_id = payload.get("external_task_id") or task_data.get("external_task_id")
                    framework = payload.get("framework") or task_data.get("framework")
                    agent_id = payload.get("agent_id")
                    cases = payload.get("cases", []) or []
                    real_cases = [case for case in cases if isinstance(case, dict) and case.get("case_id")]
                    case_count = len(real_cases)

                    print(f"\n[+] 收到任务: {task_id} (类型: {task_type})")
                    print(
                        f"    [-] topic={topic_partition.topic}, partition={message.partition}, "
                        f"offset={message.offset}, key={message.key!r}"
                    )
                    print(
                        f"    [-] external_task_id={external_task_id}, framework={framework}, "
                        f"agent_id={agent_id}, 解析到真实用例数={case_count}"
                    )
                    print("    [-] 原始任务消息:")
                    print(pretty_json(task_data))

                    if case_count == 0:
                        print("    [!] 任务中没有可执行的 cases，跳过")
                        continue

                    print("    [-] 解析后的用例列表:")
                    for index, case_item in enumerate(real_cases, start=1):
                        print(f"        {summarize_case(case_item, index, case_count)}")

                    total_delay = 0.0
                    finished_cases = 0
                    failed_cases = 0

                    for index, case_item in enumerate(real_cases, start=1):
                        case_id = case_item.get("case_id")
                        case_title = (
                            case_item.get("case_title")
                            or case_item.get("title")
                            or case_item.get("auto_case_id")
                            or case_id
                        )

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
                        producer.send(DEFAULT_TEST_EVENTS_TOPIC, case_start_event)
                        print(f"    [-] 已发送 case_start: {case_id}")
                        print(pretty_json(case_start_event))

                        delay = random.uniform(delay_min, delay_max)
                        total_delay += delay
                        print(f"    [-] 模拟执行中: case_id={case_id}, delay={delay:.2f}s")
                        time.sleep(delay)

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
                        producer.send(DEFAULT_TEST_EVENTS_TOPIC, case_finish_event)
                        print(f"    [-] 已发送 case_finish: {case_id} ({finished_cases}/{case_count})")
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
                    producer.send(DEFAULT_TEST_EVENTS_TOPIC, task_finish_event)
                    print("    [-] 已发送 task_finish 事件")
                    print(pretty_json(task_finish_event))

                    result_message = build_result_message(task_id, total_delay, case_count)
                    producer.send(DEFAULT_RESULT_TOPIC, result_message)
                    print("    [-] 已发送结果消息")
                    print(pretty_json(result_message))
                    print(
                        f"    [+] 任务完成: {task_id}, case_count={case_count}, "
                        f"finished_cases={finished_cases}, failed_cases={failed_cases}, "
                        f"total_delay={total_delay:.2f}s"
                    )

        except KeyboardInterrupt:
            # 用户按下 Ctrl+C
            print("\n[*] 收到中断信号，正在关闭...")
            break
        except Exception as e:
            # 其他异常，打印错误后继续
            print(f"[!] 错误: {e}")
            print(traceback.format_exc())
            time.sleep(1)


def main():
    """
    程序入口点。

    初始化 Kafka 消费者和生产者，启动模拟执行循环。
    """
    # 解析命令行参数
    args = parse_args()

    print(f"[*] 连接 Kafka: {args.bootstrap_servers}")
    print(f"[*] Consumer Group: {args.group_id}")
    print(
        f"[*] 平台注册配置: platform_url={args.platform_url}, agent_id={args.agent_id}, "
        f"host={args.host}, port={args.port}, region={args.region}"
    )

    # 验证延迟参数
    if args.delay_min > args.delay_max:
        print("[!] 错误: --delay-min 不能大于 --delay-max")
        sys.exit(1)

    if args.delay_min < 0 or args.delay_max < 0:
        print("[!] 错误: 延迟参数不能为负数")
        sys.exit(1)

    # 创建 Kafka 消费者和生产者
    consumer = create_consumer(args.bootstrap_servers, args.group_id)
    producer = create_producer(args.bootstrap_servers)
    framework_client = FrameworkClient(
        platform_url=args.platform_url,
        agent_id=args.agent_id,
        host=args.host,
        port=args.port,
        region=args.region,
        heartbeat_interval=args.heartbeat_interval,
        heartbeat_ttl_seconds=args.heartbeat_ttl,
    )
    stop_event = threading.Event()
    heartbeat_thread = None

    try:
        framework_client.register_agent()
        framework_client.send_heartbeat()
        heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            args=(framework_client, stop_event),
            daemon=True,
            name="mock-framework-heartbeat",
        )
        heartbeat_thread.start()
    except Exception as exc:
        print(f"[agent] 注册或初始心跳失败: {exc}")
        print(traceback.format_exc())
        consumer.close()
        producer.close()
        sys.exit(1)

    # 设置信号处理（优雅退出）
    def signal_handler(sig, frame):
        print("\n[*] 收到终止信号")
        stop_event.set()
        consumer.close()
        producer.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号

    try:
        # 启动模拟执行循环
        simulate_execution(
            consumer=consumer,
            producer=producer,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
        )
    finally:
        # 清理资源
        stop_event.set()
        if heartbeat_thread is not None and heartbeat_thread.is_alive():
            heartbeat_thread.join(timeout=2)
        consumer.close()
        producer.close()
        print("[*] 资源已释放")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock Test Framework Client - 模拟测试框架执行器

用途：
    该脚本模拟一个测试框架执行器，用于与 dmlv4 后端系统进行联调测试。
    它从 Kafka 的 dmlv4.tasks topic 消费任务，模拟执行后返回 mock 结果和测试事件。

功能：
    1. 消费 dmlv4.tasks topic 中的任务消息
    2. 模拟任务执行（随机延迟）
    3. 发送执行结果到 dmlv4.results topic
    4. 发送测试事件到 test-events topic（started/passed/finished 序列）

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
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

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

# 执行延迟配置（秒）
DEFAULT_DELAY_MIN = 0.5   # 最小延迟
DEFAULT_DELAY_MAX = 2.0   # 最大延迟

# Mock 测试用例数量
DEFAULT_CASE_COUNT = 2


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
    parser.add_argument(
        "--case-count",
        type=int,
        default=DEFAULT_CASE_COUNT,
        help="生成的 mock 测试用例数量 (default: %(default)s)",
    )

    return parser.parse_args()


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
    event_type: str,
    status: str,
    case_count: int,
    case_seq: int | None = None,
    case_id: str | None = None,
    case_title: str | None = None,
) -> dict[str, Any]:
    """
    构建测试事件消息。

    测试事件遵循 TestEvent schema，需要包含以下关键字段：
    - schema: 必须以 "-test-event@1" 结尾
    - event_id: 唯一事件 ID
    - task_id: 关联的任务 ID
    - timestamp: 事件时间戳
    - event_type: 事件类型 (started/passed/finished)
    - status: 状态 (running/passed/failed)

    参数:
        task_id: 任务 ID
        event_type: 事件类型 ("started" | "passed" | "finished")
        status: 状态 ("running" | "passed" | "failed")
        case_count: 总测试用例数
        case_seq: 测试用例序号（passed 事件时使用）
        case_id: 测试用例 ID（passed 事件时使用）
        case_title: 测试用例标题（passed 事件时使用）

    返回:
        dict: 测试事件字典，可直接序列化为 JSON 发送到 Kafka
    """
    # 获取当前时间（UTC 时区）
    now = datetime.now(timezone.utc)

    # 基础事件结构
    event = {
        "schema": "mock-test-event@1",  # 必须以 "-test-event@1" 结尾
        "event_id": str(uuid.uuid4()),   # 唯一事件 ID
        "task_id": task_id,               # 关联的任务 ID
        "timestamp": now.isoformat(),    # ISO 格式时间戳
        "event_type": event_type,         # 事件类型
        "status": status,                 # 状态
        "total_cases": case_count,       # 总测试用例数
        "started_cases": 0,              # 已开始用例数
        "finished_cases": 0,             # 已完成用例数
        "failed_cases": 0,               # 失败用例数
    }

    # 根据事件类型添加特定字段
    if event_type == "started":
        # 任务开始事件
        event["phase"] = "start"

    elif event_type == "passed":
        # 测试用例通过事件
        event["seq"] = case_seq              # 事件序号（JSON 字段名为 seq）
        event["case_id"] = case_id           # 测试用例 ID
        event["case_title"] = case_title     # 测试用例标题
        event["started_cases"] = case_seq    # 已开始用例数
        event["finished_cases"] = case_seq   # 已完成用例数

    elif event_type == "finished":
        # 任务完成事件
        event["phase"] = "end"
        event["started_cases"] = case_count  # 全部开始
        event["finished_cases"] = case_count # 全部完成

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
    case_count: int,
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
        case_count: Mock 测试用例数量
    """
    import random

    print(f"[*] Mock Test Framework Client 已启动")
    print(f"[*] 监听 Topic: {DEFAULT_TASK_TOPIC}")
    print(f"[*] 执行延迟范围: {delay_min}-{delay_max}秒, 测试用例数: {case_count}")
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

                    print(f"\n[+] 收到任务: {task_id} (类型: {task_type})")

                    # ---------- 发送 started 事件 ----------
                    started_event = build_test_event(
                        task_id=task_id,
                        event_type="started",
                        status="running",
                        case_count=case_count,
                    )
                    producer.send(DEFAULT_TEST_EVENTS_TOPIC, started_event)
                    print(f"    [-] 已发送 started 事件")

                    # ---------- 模拟任务执行 ----------
                    # 随机延迟模拟真实执行时间
                    delay = random.uniform(delay_min, delay_max)
                    time.sleep(delay)

                    # ---------- 发送 passed 事件 ----------
                    # 为每个测试用例发送一个 passed 事件
                    for i in range(1, case_count + 1):
                        passed_event = build_test_event(
                            task_id=task_id,
                            event_type="passed",
                            status="passed",
                            case_count=case_count,
                            case_seq=i,
                            case_id=f"mock-case-{i}",
                            case_title=f"Mock Test Case {i}",
                        )
                        producer.send(DEFAULT_TEST_EVENTS_TOPIC, passed_event)
                        print(f"    [-] 已发送 passed 事件: case {i}/{case_count}")

                    # ---------- 发送 finished 事件 ----------
                    finished_event = build_test_event(
                        task_id=task_id,
                        event_type="finished",
                        status="passed",
                        case_count=case_count,
                    )
                    producer.send(DEFAULT_TEST_EVENTS_TOPIC, finished_event)
                    print(f"    [-] 已发送 finished 事件")

                    # ---------- 发送结果消息 ----------
                    result_message = build_result_message(task_id, delay, case_count)
                    producer.send(DEFAULT_RESULT_TOPIC, result_message)
                    print(f"    [+] 任务完成: {task_id}")

        except KeyboardInterrupt:
            # 用户按下 Ctrl+C
            print("\n[*] 收到中断信号，正在关闭...")
            break
        except Exception as e:
            # 其他异常，打印错误后继续
            print(f"[!] 错误: {e}")
            time.sleep(1)


def main():
    """
    程序入口点。

    初始化 Kafka 消费者和生产者，启动模拟执行循环。
    """
    # 解析命令行参数
    args = parse_args()

    print(f"[*] 连接 Kafka: {args.bootstrap_servers}")

    # 验证延迟参数
    if args.delay_min > args.delay_max:
        print("[!] 错误: --delay-min 不能大于 --delay-max")
        sys.exit(1)

    if args.delay_min < 0 or args.delay_max < 0:
        print("[!] 错误: 延迟参数不能为负数")
        sys.exit(1)

    if args.case_count < 1:
        print("[!] 错误: --case-count 至少为 1")
        sys.exit(1)

    # 创建 Kafka 消费者和生产者
    consumer = create_consumer(args.bootstrap_servers, args.group_id)
    producer = create_producer(args.bootstrap_servers)

    # 设置信号处理（优雅退出）
    def signal_handler(sig, frame):
        print("\n[*] 收到终止信号")
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
            case_count=args.case_count,
        )
    finally:
        # 清理资源
        consumer.close()
        producer.close()
        print("[*] 资源已释放")


if __name__ == "__main__":
    main()
# Mock 测试框架客户端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发一个轻量级独立 Python 脚本，模拟测试框架执行器，从 Kafka 消费任务并返回 mock 结果和测试事件。

**Architecture:** 独立脚本模式，使用 kafka-python 库。消费 dmlv4.tasks，发送结果到 dmlv4.results，发送测试事件到 test-events。

**Tech Stack:** Python, kafka-python, pydantic

**设计文档:** 见 `docs/superpowers/specs/2026-03-19-mock-test-framework-client-design.md`

---

## 文件结构

```
backend/
└── scripts/
    └── mock_test_framework.py    # 主脚本（新建）
```

---

## Task 1: 创建 Mock 测试框架脚本

**Files:**
- Create: `backend/scripts/mock_test_framework.py`

- [ ] **Step 1: 创建脚本文件结构**

```python
#!/usr/bin/env python3
"""Mock Test Framework Client - 模拟测试框架执行器。"""

import argparse
import json
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import kafka
from kafka import KafkaConsumer, KafkaProducer


# 默认配置
DEFAULT_BOOTSTRAP_SERVERS = "10.17.154.252:9092"
DEFAULT_TASK_TOPIC = "dmlv4.tasks"
DEFAULT_RESULT_TOPIC = "dmlv4.results"
DEFAULT_TEST_EVENTS_TOPIC = "test-events"
DEFAULT_GROUP_ID = "dmlv4-mock-executor"
DEFAULT_DELAY_MIN = 0.5
DEFAULT_DELAY_MAX = 2.0
DEFAULT_CASE_COUNT = 2


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Mock Test Framework Client")
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", DEFAULT_BOOTSTRAP_SERVERS),
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=DEFAULT_DELAY_MIN,
        help="Minimum execution delay in seconds",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=DEFAULT_DELAY_MAX,
        help="Maximum execution delay in seconds",
    )
    parser.add_argument(
        "--case-count",
        type=int,
        default=DEFAULT_CASE_COUNT,
        help="Number of mock test cases to generate",
    )
    parser.add_argument(
        "--group-id",
        default=DEFAULT_GROUP_ID,
        help="Consumer group ID",
    )
    return parser.parse_args()


def create_consumer(bootstrap_servers: str, group_id: str) -> KafkaConsumer:
    """创建 Kafka consumer。"""
    return KafkaConsumer(
        DEFAULT_TASK_TOPIC,
        bootstrap_servers=bootstrap_servers.split(","),
        group_id=group_id,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )


def create_producer(bootstrap_servers: str) -> KafkaProducer:
    """创建 Kafka producer。"""
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
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
    """构建测试事件。"""
    now = datetime.now(timezone.utc)
    event = {
        "schema": "mock-test-event@1",
        "event_id": str(uuid.uuid4()),
        "task_id": task_id,
        "timestamp": now.isoformat(),
        "event_type": event_type,
        "status": status,
        "total_cases": case_count,
        "started_cases": 0,
        "finished_cases": 0,
        "failed_cases": 0,
    }

    if event_type == "started":
        event["phase"] = "start"
    elif event_type == "passed":
        event["seq"] = case_seq
        event["case_id"] = case_id
        event["case_title"] = case_title
        event["started_cases"] = case_seq
        event["finished_cases"] = case_seq
    elif event_type == "finished":
        event["phase"] = "end"
        event["started_cases"] = case_count
        event["finished_cases"] = case_count

    return event


def build_result_message(task_id: str, duration: float, case_count: int) -> dict[str, Any]:
    """构建结果消息。"""
    return {
        "task_id": task_id,
        "status": "success",
        "result_data": {
            "duration": round(duration, 2),
            "summary": f"{case_count} passed",
        },
        "executor": "mock-executor",
        "complete_time": datetime.now(timezone.utc).isoformat(),
    }


def simulate_execution(
    consumer: KafkaConsumer,
    producer: KafkaProducer,
    delay_min: float,
    delay_max: float,
    case_count: int,
) -> None:
    """模拟执行循环。"""
    print(f"[*] Mock Test Framework Client started")
    print(f"[*] Listening on topic: {DEFAULT_TASK_TOPIC}")
    print(f"[*] Delay range: {delay_min}-{delay_max}s, Case count: {case_count}")

    while True:
        try:
            # 拉取消息
            records = consumer.poll(timeout_ms=1000)

            for topic_partition, messages in records.items():
                for message in messages:
                    task_data = message.value
                    task_id = task_data.get("task_id", "unknown")
                    task_type = task_data.get("task_type", "unknown")

                    print(f"\n[+] Received task: {task_id} (type: {task_type})")

                    # 发送 started 事件
                    started_event = build_test_event(
                        task_id=task_id,
                        event_type="started",
                        status="running",
                        case_count=case_count,
                    )
                    producer.send(DEFAULT_TEST_EVENTS_TOPIC, started_event)
                    print(f"    [-] Sent started event")

                    # 模拟执行延迟
                    import random
                    delay = random.uniform(delay_min, delay_max)
                    time.sleep(delay)

                    # 发送 passed 事件（每个测试用例）
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
                        print(f"    [-] Sent passed event: case {i}/{case_count}")

                    # 发送 finished 事件
                    finished_event = build_test_event(
                        task_id=task_id,
                        event_type="finished",
                        status="passed",
                        case_count=case_count,
                    )
                    producer.send(DEFAULT_TEST_EVENTS_TOPIC, finished_event)
                    print(f"    [-] Sent finished event")

                    # 发送结果消息
                    result_message = build_result_message(task_id, delay, case_count)
                    producer.send(DEFAULT_RESULT_TOPIC, result_message)
                    print(f"    [+] Task completed: {task_id}")

        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
            break
        except Exception as e:
            print(f"[!] Error: {e}")
            time.sleep(1)


def main():
    """主入口。"""
    args = parse_args()

    print(f"[*] Connecting to Kafka: {args.bootstrap_servers}")

    # 创建 consumer 和 producer
    consumer = create_consumer(args.bootstrap_servers, args.group_id)
    producer = create_producer(args.bootstrap_servers)

    # 设置信号处理
    def signal_handler(sig, frame):
        print("\n[*] Received interrupt signal")
        consumer.close()
        producer.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        simulate_execution(
            consumer=consumer,
            producer=producer,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            case_count=args.case_count,
        )
    finally:
        consumer.close()
        producer.close()
        print("[*] Resources cleaned up")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本验证语法**

```bash
cd backend
python -m py_compile scripts/mock_test_framework.py
echo "Syntax OK"
```

Expected: 无错误输出

- [ ] **Step 3: 提交代码**

```bash
git add backend/scripts/mock_test_framework.py
git commit -m "feat: 添加 Mock 测试框架客户端脚本

- 消费 dmlv4.tasks 任务
- 发送 mock 结果到 dmlv4.results
- 发送测试事件到 test-events
- 支持命令行参数配置

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 验证实现

**Files:**
- Test: `backend/scripts/mock_test_framework.py`

- [ ] **Step 1: 测试脚本可以正常执行**

```bash
cd backend
python scripts/mock_test_framework.py --help
```

Expected: 显示帮助信息，包含 --bootstrap-servers, --delay-min, --delay-max, --case-count, --group-id 等参数

- [ ] **Step 2: 测试事件构建函数**

```bash
cd backend
python -c "
from scripts.mock_test_framework import build_test_event

# 测试 started 事件
event = build_test_event('task-001', 'started', 'running', 2)
assert event['schema'] == 'mock-test-event@1'
assert event['event_type'] == 'started'
assert event['task_id'] == 'task-001'
print('started event OK')

# 测试 passed 事件
event = build_test_event('task-001', 'passed', 'passed', 2, case_seq=1, case_id='mock-case-1', case_title='Mock Test Case 1')
assert event['seq'] == 1
assert event['case_id'] == 'mock-case-1'
print('passed event OK')

# 测试 finished 事件
event = build_test_event('task-001', 'finished', 'passed', 2)
assert event['started_cases'] == 2
assert event['finished_cases'] == 2
print('finished event OK')

print('All tests passed!')
"
```

Expected: All tests passed!

- [ ] **Step 3: 测试结果消息构建**

```bash
cd backend
python -c "
from scripts.mock_test_framework import build_result_message

msg = build_result_message('task-001', 1.5, 3)
assert msg['task_id'] == 'task-001'
assert msg['status'] == 'success'
assert msg['executor'] == 'mock-executor'
assert msg['result_data']['summary'] == '3 passed'
print('Result message OK')
"
```

Expected: Result message OK

- [ ] **Step 4: 提交验证**

```bash
git add -A
git commit -m "test: 验证 Mock 测试框架脚本

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 验收标准检查

实现完成后验证以下内容：

1. **脚本可执行**: `python scripts/mock_test_framework.py --help` 显示帮助信息
2. **Kafka 连接**: 脚本能成功连接到配置的 Kafka 服务器
3. **消息发送**: 能正确发送 ResultMessage 到 dmlv4.results
4. **事件发送**: 能正确发送 TestEvent 序列（started/passed/finished）到 test-events
5. **优雅退出**: Ctrl+C 能正确关闭资源
6. **日志输出**: 有清晰的执行日志

---

## 依赖说明

脚本使用 `kafka-python` 库。确保已安装：

```bash
pip install kafka-python
```

或者复用项目 requirements.txt 中的依赖。
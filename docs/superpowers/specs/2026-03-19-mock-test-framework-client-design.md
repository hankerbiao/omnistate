# Mock 测试框架客户端设计

## 概述

开发一个轻量级独立 Python 脚本，模拟测试框架执行器。它从 Kafka `dmlv4.tasks` topic 消费任务，模拟执行后返回 mock 结果和测试事件，与现有 dmlv4 项目联调。

## 目标

- 最小化实现复杂度
- 支持与现有后端系统联调
- 兼容现有 Kafka topic 和消息格式

## 架构

```
┌─────────────────┐     dmlv4.tasks      ┌──────────────────┐
│  真实后端系统   │ ───────────────────→ │  Mock 客户端     │
│                 │                      │  (Python 脚本)   │
└─────────────────┘                      └────────┬─────────┘
                                                  │
                        dmlv4.results ←───────────┤
                        test-events ←─────────────┘
```

## 功能需求

### 2.1 任务消费

- 订阅 `dmlv4.tasks` topic
- 使用 group_id: `dmlv4-mock-executor`
- 解析 TaskMessage，提取 task_id 和 task_type

### 2.2 Mock 结果返回

- 模拟执行延迟：随机 0.5-2 秒
- 结果状态：固定返回 `success`
- 结果数据：包含基本的执行信息（耗时、输出摘要）
- 发送到 `dmlv4.results` topic

### 2.3 测试事件发送

发送以下事件序列（参考现有 schema: `backend/app/modules/execution/schemas/kafka_events.py`）：

1. **started 事件** - 任务开始时
   - schema: "mock-test-event@1" (必须以 -test-event@1 结尾)
   - event_id: UUID 字符串
   - task_id: 从消费的任务中提取
   - timestamp: 当前时间 ISO 格式
   - event_type: "started"
   - status: "running"
   - total_cases: 配置的测试用例数
   - started_cases: 0
   - finished_cases: 0
   - failed_cases: 0

2. **passed 事件** - 每个测试用例通过时发送（数量由 --case-count 配置）
   - schema: "mock-test-event@1"
   - event_id: UUID 字符串（每个事件唯一）
   - task_id: 从消费的任务中提取
   - timestamp: 当前时间 ISO 格式
   - event_type: "passed"
   - status: "passed"
   - event_seq: 序号（1, 2, 3...）
   - case_id: "mock-case-{seq}"
   - case_title: "Mock Test Case {seq}"
   - total_cases: 配置的测试用例数
   - started_cases: 当前序号
   - finished_cases: 当前序号
   - failed_cases: 0

3. **finished 事件** - 任务完成时
   - schema: "mock-test-event@1"
   - event_id: UUID 字符串
   - task_id: 从消费的任务中提取
   - timestamp: 当前时间 ISO 格式
   - event_type: "finished"
   - status: "passed"
   - total_cases: 配置的测试用例数
   - started_cases: 配置的测试用例数
   - finished_cases: 配置的测试用例数
   - failed_cases: 0

发送到 `test-events` topic。

### 2.4 配置

通过命令行参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --bootstrap-servers | 10.17.154.252:9092 | Kafka 地址 |
| --delay-min | 0.5 | 最小执行延迟(秒) |
| --delay-max | 2.0 | 最大执行延迟(秒) |
| --case-count | 2 | 生成的 mock 测试用例数 |
| --group-id | dmlv4-mock-executor | Consumer group ID |

也可通过环境变量：
- `KAFKA_BOOTSTRAP_SERVERS` - 覆盖 --bootstrap-servers

## 实现要点

### 3.1 代码结构

```
backend/
└── scripts/
    └── mock_test_framework.py    # 主脚本
```

### 3.2 依赖

- kafka-python
- pydantic（复用现有）

### 3.3 消息格式参考

参考现有代码中的 schema 定义：
- **TaskMessage**: `backend/app/shared/kafka/producer.py` - TaskMessage 类
- **ResultMessage**: `backend/app/shared/kafka/producer.py` - ResultMessage 类
- **TestEvent**: `backend/app/modules/execution/schemas/kafka_events.py` - TestEvent 类

ResultMessage 构造示例：
- task_id: 从消费的任务中提取
- status: "success"
- result_data: {"duration": 1.23, "summary": "2 passed"}
- executor: "mock-executor"
- complete_time: 当前时间 ISO 格式

### 3.4 运行方式

```bash
cd backend
python scripts/mock_test_framework.py

# 或带参数
python scripts/mock_test_framework.py --delay-min 1 --delay-max 3 --case-count 3
```

## 验收标准

1. 脚本启动后能成功连接 Kafka
2. 收到任务后能发送 ResultMessage 到 dmlv4.results
3. 发送的测试事件能被后端正确解析（符合 TestEvent schema）
4. 可通过 Ctrl+C 优雅退出
5. 日志输出清晰的执行过程

## 非目标（V1）

- 不支持根据 task_id 返回不同结果
- 不支持配置文件
- 不需要 Web UI 或 API
- 不需要错误模拟（fail 场景）
# Mock RabbitMQ Consumer 逻辑说明

## 目标

`backend/scripts/mock_rabbitmq_consumer.py` 的职责是模拟一个执行端：

1. 从 RabbitMQ 任务队列消费平台下发的任务消息
2. 按当前任务 payload 中的 `cases` 做最小 mock 执行
3. 将 mock 执行过程中的测试事件发送到 Kafka `test-events`
4. 将 mock 执行结果发送到 Kafka `dmlv4.results`

它用于验证以下联调链路：

`DML V4 后端 -> RabbitMQ -> mock consumer -> Kafka -> DML V4 结果消费链路`

## 输入

脚本从 RabbitMQ 的任务队列读取消息，消息体是平台实际发送的纯任务 payload：

```json
{
  "task_id": "ET-2026-000001",
  "category": "bmc",
  "project_tag": "universal",
  "repo_url": "http://git.example.com/qa/cases.git",
  "branch": "master",
  "cases": [
    {
      "case_id": "TC-1",
      "script_path": "tests/test_demo.py",
      "script_name": "test_demo",
      "parameters": {
        "env": "qa"
      }
    }
  ],
  "pytest_options": {
    "task_id": "ET-2026-000001"
  },
  "timeout": 300
}
```

## 处理流程

### 1. 启动阶段

脚本启动时读取三类共享配置：

- RabbitMQ 配置：来自 `app.shared.rabbitmq.config`
- Kafka 配置：来自 `app.shared.kafka.config`
- 平台代理配置：默认读取 `MOCK_PLATFORM_URL`、`MOCK_AGENT_ID`、`MOCK_AGENT_HOST`、
  `MOCK_AGENT_PORT`、`MOCK_AGENT_REGION`、`MOCK_HEARTBEAT_INTERVAL`、
  `MOCK_HEARTBEAT_TTL`

脚本不接收命令行参数，全部走默认配置或环境变量覆盖。

在真正开始消费前，脚本会先：

1. 调用 `POST /api/v1/execution/agents/register` 注册代理
2. 立即发送一次 `ONLINE` 心跳
3. 启动后台线程，定时调用 `POST /api/v1/execution/agents/{agent_id}/heartbeat`

脚本退出时会再发送一次 `OFFLINE` 心跳。

### 2. RabbitMQ 消费

脚本建立 RabbitMQ 连接后：

- 监听任务队列
- 关闭 `auto_ack`
- 每次收到一条消息后直接解析为任务 payload
- 读取 `cases`

如果消息处理成功：

- `basic_ack`

如果消息处理失败：

- `basic_nack(requeue=False)`，避免坏消息无限重试

### 3. Mock 执行

对于每条 case，脚本按固定流程模拟：

1. 发送 `case_start`
2. 发送多条 `assert` 事件，模拟断言/步骤明细
3. 休眠一个固定的极短延迟
4. 发送 `case_finish`

全部 case 完成后：

1. 发送 `collection_finish`
2. 发送 `task_finish`
3. 发送 `result message`

当前脚本默认所有 case 都返回 `PASSED`，结果消息固定为 `success`。
但事件中的 `data`、`nodeid`、断言明细、耗时、仓库信息、参数快照等字段
会尽量补充得更完整，便于平台前端和排障链路展示更多 mock 细节。

## 输出到 Kafka 的消息

### 测试事件

发送到 `test-events` topic，schema 为：

- `schema = "mock-test-event@1"`

事件阶段包含：

- `collection_start`
- `case_start`
- `assert`
- `case_finish`
- `collection_finish`
- `task_finish`

其中：

- `progress` 事件会带 `phase`
- `assert` 事件会带 `name`、`seq`、`data.expected`、`data.actual`、`data.message`
- case 相关事件会带 `nodeid`、`project_tag`
- `data` 中会补充 `script_path`、`script_name`、`parameters`、`duration_ms`、`worker`

### 结果消息

发送到 `dmlv4.results` topic，字段对齐现有 execution 结果消费链路：

- `task_id`
- `status`
- `result_data`
- `executor`
- `complete_time`

其中 `result_data` 会附带：

- 总耗时
- 通过/失败 case 数
- 每条 case 的脚本名、脚本路径、状态、耗时摘要

## 调试输出

脚本会打印：

- 收到的 RabbitMQ 任务消息
- 代理注册响应
- 定时心跳发送结果
- 每条发送到 Kafka 的 test event
- 最终 result message

这样可以同时观察：

- RabbitMQ 输入是否正确
- mock 执行流程是否走通
- Kafka 回写格式是否符合预期

## 适用场景

这个脚本适合以下场景：

- 验证 RabbitMQ 下发链路是否通
- 验证 Kafka 结果与事件回传是否通
- 在没有真实执行 agent 时做平台联调

## 不做的事情

当前脚本明确不负责：

- 真正执行测试脚本
- 根据用例内容动态判定失败
- 回调 HTTP
- 长期保存执行日志

它的目标只是作为一个最小、稳定、可观察的 mock 执行端。

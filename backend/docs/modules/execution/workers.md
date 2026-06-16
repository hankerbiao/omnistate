# Execution Worker 与消息

execution 的状态推进依赖 **Kafka `test-events`**（主路径）。任务下发仅通过 **RabbitMQ**。

## Kafka Worker 是独立进程

Kafka Worker **不会**随 FastAPI 主服务自动启动，需要手动运行。

```bash
python -m app.workers.kafka_worker_main
```

如果只启动 FastAPI 服务而不启动 Kafka Worker，自动化测试的执行结果**无法回写**到 MongoDB，页面上的任务状态会一直停留在"执行中"。

### 主服务启动时的健康检查

从 v2.0.0 开始，FastAPI 主服务启动时新增了 Kafka 健康检查（`check_kafka_health()`），检测两项内容：

1. **Kafka Broker 连通性**：通过 TCP 连接 `bootstrap_servers`，确认 Kafka 服务可达
2. **Kafka Worker 心跳**：查询 MongoDB `execution_agents` 集合，检查 Worker 进程的心跳记录是否有效

任一检查失败，主服务会拒绝启动并给出明确指引：

```
ERROR    Kafka 基础设施不健康: Kafka Worker 未运行
ERROR    请确保 Kafka Broker 和 Kafka Worker 进程已就绪
ERROR    启动 Kafka Worker: python -m app.workers.kafka_worker_main
```

### 生产部署

两个进程都需要运行：

```bash
# 终端 1: FastAPI 服务
./server.sh start

# 终端 2: Kafka Worker（独立进程）
python -m app.workers.kafka_worker_main
```

### 健康检查源码入口

- 检查逻辑：`app/shared/kafka/health.py`
- 主服务集成：`app/main.py` 的 `lifespan` 函数

## Kafka 消费

### 入口

- **进程**：`python -m app.workers.kafka_worker_main`
- **注册**：`register_execution_kafka_handlers()` in `application/kafka_handlers.py`
- **运行时**：`app/shared/kafka/consumer.py` — `KafkaConsumerRunner`

### 订阅 Topic（配置驱动）

见 `config.yaml` 的 `kafka` 段，典型包括：

- **test-events**：细粒度测试事件（驱动状态机）
- **result**（若配置）：任务级结果消息（当前多为日志留痕）

Handler 仅在 router 中注册了 handler 的 topic 会被订阅。

### 消息处理链

```
KafkaConsumerRunner._poll_runtime
  └─ trace_scope(request_id=kafka:topic:partition:offset)
       └─ KafkaTopicHandlerRegistry.dispatch
            └─ ExecutionKafkaHandlers
                 ├─ handle_test_event → ExecutionEventIngestService
                 └─ handle_result_event → 日志 only
```

### Schema 路由

`handle_test_event` 根据 payload 内 `schema` 后缀：

- `*-test-event@1` → 单条 ingest
- `*-test-event-batch@1` → 拆 batch 后逐条 ingest（单条失败不阻塞整批）

不支持的 schema 抛错 → 进入死信流程（见下）。

### 幂等

- 消费前：`ExecutionEventDoc.find_one({ event_id })`
- 插入时：捕获并发重复插入 → 视为 duplicate skip

### 死信（DLQ）

Handler 异常时：

1. 写入 dead-letter topic（含原始 payload、error、metadata）
2. DLQ 成功则 commit offset；DLQ 失败则不 commit，重启后重试

## RabbitMQ 下发

- **实现**：`service/task_dispatcher.py` → `_dispatch_via_rabbitmq`
- **消息**：`TaskMessage(task_type="execution_task", task_data=...)`
- **队列**：由 `config.yaml` `rabbitmq` 段配置（如 `dml_task_queue`）

Agent 侧消费队列执行 case，并向 Kafka 回报事件（与 RabbitMQ 消费解耦）。

## Worker 与 MongoDB

`kafka_worker_main` 启动时注册 Beanie 模型包括：

- `ExecutionTaskDoc`、`ExecutionTaskCaseDoc`、`ExecutionEventDoc`
- `ExecutionBizLogDoc`（业务轨迹写入）
- 以及 workflow / auth / test_specs 等 worker 可能触达的模型

## 本地联调

使用仓库脚本模拟执行端：

```bash
cd backend
python scripts/mock_test_framework.py
```

详见根目录 [测试执行编排](../../../../docs/guide/test-execution.md) 联调章节。

## 修改清单

| 需求 | 文件 |
|------|------|
| 新 topic / schema | `kafka_handlers.py`、`config.yaml`、router 注册 |
| 改事件聚合 | `event_ingest_service.py` |
| 改消费 trace | `app/shared/kafka/consumer.py` |
| 改死信行为 | `consumer.py`、`dead_letter.py` |

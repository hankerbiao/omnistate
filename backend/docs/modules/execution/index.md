# Execution 模块

`execution` 是 DML V4 的**测试任务编排核心模块**：负责创建执行任务、串行下发 case、消费执行端事件、自动推进下一条 case，并维护任务/case 的**当前态**。

## 文档导航

| 文档 | 内容 |
|------|------|
| [架构与进程](./architecture.md) | 多进程架构、串行编排模型、端到端数据流 |
| [数据模型](./data-models.md) | MongoDB 集合、字段含义、`ExecutionBizLogDoc` |
| [状态与流转](./state-and-flow.md) | 状态枚举、自动推进条件、事件映射规则 |
| [HTTP API](./api.md) | 路由、权限、请求/响应约定 |
| [日志与排障](./logging.md) | 结构化日志、`ExecutionNode`、Runbook |
| [Worker 与消息](./workers.md) | Kafka / RabbitMQ、Handler 注册、死信 |

仓库内代码说明见 [`app/modules/execution/README.md`](../../../app/modules/execution/README.md)。  
项目级联调说明见仓库根目录 [`docs/guide/test-execution.md`](../../../../docs/guide/test-execution.md)。

## 模块职责（一句话）

平台**一次只下发 1 条 case**；执行端通过 Kafka `test-events` 回报进度；平台更新当前态后，在 `case_finish` 时决定是否下发下一条或收口任务。

## 核心目录

```
app/modules/execution/
├── api/routes.py                 # HTTP 入口
├── application/
│   ├── task_command_service.py   # 创建 / 删除 / 重跑
│   ├── task_dispatch_service.py  # 创建任务文档 + 触发下发
│   ├── task_dispatch_coordinator.py  # 单 case 下发与状态回写
│   ├── task_query_service.py     # 列表 / 状态 / 业务轨迹
│   ├── event_ingest_service.py   # Kafka 事件入库与聚合
│   ├── progress_coordinator.py   # case 完成后自动推进
│   └── kafka_handlers.py         # Kafka topic 路由
├── service/
│   ├── task_dispatcher.py        # RabbitMQ 下发
│   └── task_scheduler.py         # 定时任务扫描
├── shared/
│   ├── execution_context.py      # task_id 等业务上下文
│   └── execution_log.py          # elog / ExecutionNode
└── repository/models/            # Beanie 文档模型
```

## 关键调用链

| 场景 | 调用链 |
|------|--------|
| 创建并下发 | API → `ExecutionTaskCommandService` → `ExecutionDispatchService` → `ExecutionTaskDispatchCoordinator` → `ExecutionTaskDispatcher` |
| 查询任务 | API → `ExecutionTaskQueryService` |
| 事件驱动推进 | Kafka → `ExecutionKafkaHandlers` → `ExecutionEventIngestService` → `ExecutionProgressCoordinator` → 再次下发 |
| 定时触发 | Scheduler → `ExecutionTaskScheduler` → `ExecutionDispatchService` |

## 与其它模块的关系

- **test_specs**：通过 `auto_case_id` 解析 `AutomationTestCaseDoc`，得到 `case_id`、`script_path` 等，**不信任前端透传脚本信息**。
- **attachments**：下发前为 `parameters` 中 `type=file` 的字段注入 `download_url`。
- **auth**：任务写操作校验 `execution_tasks:write`，读操作校验 `execution_tasks:read`。
- **workflow**：无直接耦合；需求/用例的业务流转在 workflow，**执行编排**在 execution。

## 常见修改场景

| 需求 | 优先文件 |
|------|----------|
| 改创建/重跑参数 | `schemas/execution.py`、`task_command_service.py` |
| 改下发 payload | `task_command_helpers.py`、`task_dispatcher.py` |
| 改事件聚合逻辑 | `event_ingest_service.py`、`domain/status_rules.py` |
| 改自动推进规则 | `progress_coordinator.py` |
| 改日志节点 | `shared/execution_log.py` + 对应 service |
| 改 Kafka 接入 | `kafka_handlers.py`、`app/shared/kafka/consumer.py` |

## 风险点

- 抽象层次多（command / dispatch service / coordinator / dispatcher），改动前先确定落点，避免在多个文件重复补丁。
- **事件幂等**（`ExecutionEventDoc.event_id`）与**当前态更新**（task/case 表）解耦；排障时需同时看 `execution_events` 与 `execution.log`。
- 下发失败时同步反映到 `dispatch_status`；排障重点查 RabbitMQ 连接、队列配置与 Agent 消费侧日志。

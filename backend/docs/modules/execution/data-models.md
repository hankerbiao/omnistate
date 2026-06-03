# Execution 数据模型

所有 execution 相关集合使用 Beanie ODM，模型定义在 `app/modules/execution/repository/models/`。

## 模型总览

| 集合名 | 模型 | 用途 |
|--------|------|------|
| `execution_tasks` | `ExecutionTaskDoc` | 任务当前态与串行游标 |
| `execution_task_cases` | `ExecutionTaskCaseDoc` | 任务内每条 case 的当前态 |
| `execution_events` | `ExecutionEventDoc` | 外部 Kafka 事件归档（幂等） |
| `execution_biz_logs` | `ExecutionBizLogDoc` | 平台侧业务节点时间线 |

> **当前态 vs 历史**：`execution_tasks` / `execution_task_cases` 只保留**当前**状态与摘要；完整事件流在 `execution_events`；平台决策轨迹在 `execution_biz_logs`。

## ExecutionTaskDoc

任务主表，字段分组说明：

**身份与配置**

- `task_id`：业务 ID，格式 `ET-{year}-{seq}`
- `source_task_id`：重跑来源任务
- `framework`、`agent_id`、`dispatch_channel`
- `request_payload`：创建时请求快照（cases、schedule、pytest_options 等）— 详见 [去重与快照](./architecture#去重与快照)
- `dedup_key`：去重键 — 详见 [去重与快照](./architecture#去重与快照)
- `created_by`：创建人 user_id

**调度与下发**

- `schedule_type`：`IMMEDIATE` / `SCHEDULED`
- `schedule_status`：`PENDING` / `READY` / `TRIGGERED`（见 [状态与流转](./state-and-flow.md)）
- `dispatch_status`：`PENDING` → `DISPATCHED` / `DISPATCH_FAILED` / `COMPLETED`
- `dispatch_error`、`dispatch_response`：下发失败原因与通道响应

**消费与整体状态**

- `consume_status`：是否已收到执行端事件（`CONSUMED`）
- `overall_status`：对外展示的任务状态（`QUEUED` / `RUNNING` / `PASSED` / `FAILED` 等）
- `consumed_at`、`last_callback_at`

**串行游标**

- `current_case_id`：当前正在推进的 case
- `current_case_index`：当前 case 在任务中的下标（0-based）

**聚合计数**

- `case_count`、`started_case_count`、`finished_case_count`、`failed_case_count`、`passed_case_count`
- `progress_percent`、`reported_case_count`

**最近事件摘要**（便于列表页展示，非完整历史）

- `last_event_id`、`last_event_at`、`last_event_type`、`last_event_phase`

## ExecutionTaskCaseDoc

任务内单条 case 的当前态：

- `task_id` + `case_id`：联合定位
- `order_no`：执行顺序
- `status`：case 级状态（`QUEUED` / `RUNNING` / `PASSED` / `FAILED` / `SKIPPED`）
- `dispatch_status`、`dispatch_attempts`、`dispatched_at`
- `step_total` / `step_passed` / `step_failed` / `step_skipped`：由 `assert` 事件累积
- `result_data`：展示用摘要（含最近 assertions 列表，非完整步骤树）
- `failure_message`、`nodeid`、`case_title_snapshot`（运行时由事件补充，见 [去重与快照](./architecture#去重与快照)）

## ExecutionEventDoc

**外部执行端**上报事件的归档表：

- `event_id`：**唯一索引**，幂等去重
- `payload`：原始 JSON
- `metadata`：Kafka `topic` / `partition` / `offset` 等
- `processed` / `process_error`：平台是否成功应用该事件

即使任务不存在，也会尝试归档（`processed=false`），避免丢排障线索。

## ExecutionBizLogDoc

**平台侧**业务节点日志（由 `elog()` 异步写入，见 [日志与排障](./logging.md)）：

| 字段 | 说明 |
|------|------|
| `task_id` | 关联任务（必填） |
| `case_id` / `event_id` | 可选关联 |
| `node` | 业务节点，如 `task.dispatch` |
| `action` | 人类可读描述 |
| `outcome` | `success` / `failed` / `skipped` 等 |
| `status_before` / `status_after` | 状态变更快照 |
| `operator_id` | 操作人（HTTP 场景） |
| `request_id` | 链路 ID |
| `detail` | 其它结构化摘要 |
| `level` | INFO / WARNING / ERROR |

查询 API：`GET /api/v1/execution/tasks/{task_id}/biz-logs`

## 索引策略（要点）

- `execution_events.event_id`：唯一
- `execution_events`：`(task_id, event_timestamp)` 降序 — 按任务查事件
- `execution_biz_logs`：`(task_id, created_at)` 降序 — 业务时间线
- `execution_tasks.task_id`：业务主键查询

完整字段表见 [数据库表与字段](../../reference/database-tables.md#execution-相关表)。

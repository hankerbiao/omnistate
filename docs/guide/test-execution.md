# 测试执行编排

本文档描述 `execution` 模块的接口、数据模型和业务流程。

## 1. 进程架构

| 进程 | 入口 | 职责 |
|------|------|------|
| 主服务 | `app.main` | HTTP API、创建/查询任务、下发任务、定时调度 |
| Kafka Worker | `app/workers/kafka_worker_main.py` | 消费 `test-events`、更新任务状态、串行推进下一条 case |
| RabbitMQ Worker | `app/workers/rabbitmq_worker_main.py` | 消费 RabbitMQ 测试事件、委托 Kafka Handler 处理 |
| 执行代理 | 外部 | 消费任务、执行 case、向 Kafka `test-events` 回报事件 |

启动顺序：MongoDB → Kafka/RabbitMQ → Worker → 主服务 → 执行代理。

## 2. 数据模型

- **`ExecutionTaskDoc`** — 任务主表（调度状态、下发状态、整体状态、游标、聚合统计）
- **`ExecutionTaskCaseDoc`** — case 当前态（顺序、状态、断言计数、失败信息、进度）
- **`ExecutionEventDoc`** — 事件归档表（event_id 唯一索引，幂等去重）

## 3. API 接口

### 3.1 Agent 管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/execution/agents/register` | 无 | 注册/刷新代理 |
| POST | `/execution/agents/{id}/heartbeat` | 无 | 心跳上报 |
| GET | `/execution/agents` | `execution_agents:read` | 代理列表 |
| GET | `/execution/agents/{id}` | `execution_agents:read` | 代理详情 |
| DELETE | `/execution/agents/{id}` | `execution_agents:write` | 删除代理 |

### 3.2 任务管理

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/execution/tasks/dispatch` | `execution_tasks:write` | 创建并下发任务 |
| POST | `/execution/tasks/{id}/rerun` | `execution_tasks:write` | 基于快照重跑 |
| DELETE | `/execution/tasks/{id}` | `execution_tasks:write` | 逻辑删除 |
| GET | `/execution/tasks` | `execution_tasks:read` | 任务列表 |
| GET | `/execution/tasks/{id}/status` | `execution_tasks:read` | 任务状态 |

## 4. 下发请求

### 4.1 DispatchTaskRequest

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cases` | `DispatchCaseItem[]` | 是 | 用例列表，按顺序执行 |
| `dispatch_channel` | string | 是 | `RABBITMQ` 或 `HTTP` |
| `agent_id` | string | HTTP 时必填 | 目标代理 ID |
| `framework` | string | 否 | 执行框架，如 `pytest` |
| `schedule_type` | string | 否 | `IMMEDIATE`（默认）或 `SCHEDULED` |
| `planned_at` | datetime | SCHEDULED 时必填 | 计划执行时间（UTC） |
| `category` | string | 否 | 任务分类，如 `bmc` |
| `project_tag` | string | 否 | 项目标签，如 `universal` |
| `repo_url` | string | 否 | 代码仓库地址，为空时后端补默认值 |
| `branch` | string | 否 | 代码分支，为空时后端补 `master` |
| `trigger_source` | string | 否 | 触发来源，如 `web_ui` |
| `pytest_options` | object | 否 | pytest 扩展参数，与后端默认值合并 |
| `timeout` | int | 否 | 超时秒数 |
| `attachments` | `DispatchAttachmentItem[]` | 否 | 任务级共享附件 |

### 4.2 DispatchCaseItem

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `auto_case_id` | string | 是 | 自动化用例业务 ID，后端据此解析 `case_id`、`script_path`、`script_name` |
| `parameters` | object | 否 | 执行端用例参数，透传到 agent |

### 4.3 DispatchAttachmentItem

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_id` | string | 是 | 附件 ID |
| `original_filename` | string | 否 | 原始文件名 |
| `storage_path` | string | 否 | 对象存储路径 |
| `size` | int | 否 | 文件大小（字节） |
| `content_type` | string | 否 | MIME 类型 |
| `uploaded_at` | datetime | 否 | 上传时间 |

> `download_url` 由 MinIO 在下发时实时生成预签名 URL，无需前端传入。

### 4.4 请求示例

```json
{
  "framework": "pytest",
  "dispatch_channel": "HTTP",
  "agent_id": "localhost.localdomain-12.28-93f8c286",
  "trigger_source": "web_ui",
  "schedule_type": "IMMEDIATE",
  "category": "bmc",
  "project_tag": "universal",
  "pytest_options": {},
  "timeout": 300,
  "cases": [
    {
      "auto_case_id": "ATC-2026-00001",
      "parameters": {
        "target_ip": "10.10.10.100",
        "bmc_username": "admin",
        "bmc_password": "admin"
      }
    }
  ],
  "attachments": [
    {
      "file_id": "att-abc123",
      "original_filename": "config.json"
    }
  ]
}
```

### 4.5 最终下发给 Agent 的 Payload

```json
{
  "task_id": "ET-2026-000022",
  "framework": "pytest",
  "trigger_source": "web_ui",
  "category": "bmc",
  "project_tag": "universal",
  "repo_url": "http://git.internal/bmc-case.git",
  "branch": "master",
  "cases": [
    {
      "case_id": "TC-2026-00004",
      "script_path": "tests/universal/suite/fan/test_fan_basic.py",
      "script_name": "suite-fan-001",
      "parameters": {
        "target_ip": "10.10.10.100",
        "bmc_username": "admin",
        "bmc_password": "admin"
      }
    }
  ],
  "pytest_options": {
    "log_debug": false,
    "kafka_server": "10.17.154.252:9092",
    "kafka_topic": "test-events",
    "report_kafka": true,
    "maxfail": "3",
    "task_id": "ET-2026-000022"
  },
  "timeout": 300,
  "attachments": [
    {
      "file_id": "att-abc123",
      "original_filename": "config.json",
      "storage_path": "attachments/att-abc123/config.json",
      "size": 128,
      "content_type": "application/json",
      "uploaded_at": "2026-03-20T08:11:50Z",
      "download_url": "http://minio.internal/att-abc123?sign=..."
    }
  ]
}
```

> `cases` 在外发结构里永远只包含当前这 1 条。`case_id`、`script_path`、`script_name` 由后端根据 `auto_case_id` 解析。

## 5. 下发通道

任务固定通过 **RabbitMQ** 下发：

- `RabbitMQProducerManager` 将 payload 发送到 `task_queue`
- 属性：`delivery_mode=2`（持久化）、publisher confirm 已启用
- 首条 case 由主服务发出，后续 case 由 Worker 在消费到 `case_finish` 后发出

执行结果回报依赖 Kafka `test-events`，**必须运行 Kafka Worker**。

## 6. 业务流程

### 6.1 创建与下发

1. 前端 `POST /execution/tasks/dispatch`
2. 后端通过 `CaseResolver` 将 `auto_case_id` 解析为 `case_id`、`script_path`、`script_name`
3. 校验附件（`AttachmentDoc` 存在性）
4. 构建 `DispatchExecutionTaskCommand`，计算 `dedup_key`（SHA-256），检查未完成重复任务
5. 创建 `ExecutionTaskDoc` + 若干 `ExecutionTaskCaseDoc`（每 case 一条）
6. 如果是 `IMMEDIATE` 调度，立即构建第 1 条 case 的下发命令并发送

### 6.2 执行端执行

执行代理收到单 case payload 后，向 Kafka `test-events` 持续发送事件：

```
progress + phase=case_start → 若干 assert → progress + phase=case_finish
```

### 6.3 Worker 消费与状态更新

`ExecutionEventIngestService.ingest_event()` 处理每条事件：

1. `event_id` 幂等检查
2. 归档原始事件到 `ExecutionEventDoc`
3. 更新对应 `ExecutionTaskCaseDoc`（状态、时间戳、断言、进度）
4. 更新 `ExecutionTaskDoc` 聚合（case 计数、整体状态、进度）
5. 如果当前事件是 `progress + case_finish` 且 case 已进入终态：
   - 还有下一条 → 重建命令、下发下一条 case
   - 已是最后一条 → 收口任务为 `PASSED` 或 `FAILED`

### 6.4 时序图

```text
前端 → POST /dispatch → 主服务 → RabbitMQ → 执行代理
                                                      │
                                        Kafka test-events
                                                      │
                                              Kafka Worker
                                              │
                              ExecutionEventIngestService
                              ├── 更新 CaseDoc
                              ├── 更新 TaskDoc
                              └── 自动推进下一条 case
```

## 7. 状态说明

### 7.1 四类状态

| 字段 | 职责 | 典型值 |
|------|------|--------|
| `schedule_status` | 调度是否到触发阶段 | PENDING / TRIGGERED / CANCELLED |
| `dispatch_status` | 下发是否成功 | PENDING / DISPATCHED / DISPATCH_FAILED / COMPLETED |
| `consume_status` | 是否已被事件链路消费 | PENDING / CONSUMED |
| `overall_status` | 任务整体业务状态 | QUEUED / RUNNING / PASSED / FAILED |

### 7.2 任务整体状态流转

```
QUEUED ──(首条下发成功 + 收到事件)──→ RUNNING
QUEUED ──(首条下发失败)──→ FAILED
RUNNING ──(最后一条 case 完成，无失败)──→ PASSED
RUNNING ──(最后一条 case 完成，有失败)──→ FAILED
RUNNING ──(自动推进失败)──→ FAILED
```

### 7.3 case 状态流转

```
QUEUED ──(收到 case_start)──→ RUNNING
RUNNING ──(收到 case_finish，成功)──→ PASSED
RUNNING ──(收到 case_finish，失败)──→ FAILED
QUEUED/RUNNING ──(下发失败)──→ FAILED
```

## 8. 查询与前端展示

`GET /execution/tasks` 返回任务列表，每条任务 `cases` 字段包含所有 case 的当前摘要：

| 字段 | 说明 |
|------|------|
| `case_id`、`auto_case_id`、`title` | 标识信息 |
| `status`、`progress_percent` | 执行状态 |
| `dispatch_status`、`dispatch_attempts` | 下发状态 |
| `step_passed`、`step_failed`、`step_skipped` | 断言统计 |
| `failure_message` | 失败原因 |
| `started_at`、`finished_at` | 时间戳 |
| `result_data` | 扩展结果（断言明细、data、error） |

## 9. 联调

### Mock 框架

```bash
cd backend
python scripts/mock_test_framework.py
```

支持：消费 RabbitMQ 任务、按 `cases` 载荷串行执行 mock case、向 `test-events` 回报事件。

### 常见问题

| 现象 | 排查方向 |
|------|---------|
| 首条 case 执行完不继续下一条 | 确认 Kafka Worker 是否在线，确认 `test-events` 是否到达 |
| 任务列表看不到 case 细节 | 确认 `ExecutionTaskCaseDoc` 是否已创建 |

## 9.1 日志排障 Runbook

1. **拿到关联键**：用户报障时优先收集 `task_id`（如 `ET-2026-000001`）或 HTTP 响应头 `X-Request-ID`。
2. **查平台业务轨迹**：
   ```bash
   GET /api/v1/execution/tasks/{task_id}/biz-logs
   ```
3. **查 execution 域文件日志**：
   ```bash
   cat backend/logs/execution.log | jq 'select(.task_id=="ET-2026-000001")'
   ```
4. **关联 HTTP 入口**：用 `request_id` 在 `app.log` 中搜索创建/下发节点。
5. **核对 Kafka 事件**：在 MongoDB `execution_events` 集合按 `task_id` 查询，确认外部事件是否入库。
6. **自动推进未触发**：在日志中搜索 `task.advance` 节点，关注 `outcome=skipped` 及 skip 原因（case 非终态、乱序 event 等）。

## 10. 代码入口

| 文件 | 职责 |
|------|------|
| `app/modules/execution/api/routes.py` | HTTP API 路由 |
| `app/modules/execution/application/task_command_service.py` | 任务创建与重跑编排 |
| `app/modules/execution/application/task_dispatch_service.py` | 下发服务（创建、重建命令、下发已有任务） |
| `app/modules/execution/application/task_dispatch_coordinator.py` | 下发协调器（构建命令、状态更新） |
| `app/modules/execution/application/task_command_mixin.py` | 调度规范化、去重、payload 构建 |
| `app/modules/execution/application/commands.py` | `DispatchExecutionTaskCommand` 数据类 |
| `app/modules/execution/application/event_ingest_service.py` | 事件消费与状态聚合 |
| `app/modules/execution/application/progress_coordinator.py` | case 完成后自动推进 |
| `app/modules/execution/service/task_dispatcher.py` | RabbitMQ 下发实现 |
| `app/modules/execution/shared/execution_log.py` | 结构化日志 `elog()` 与业务节点枚举 |
| `app/modules/execution/shared/execution_context.py` | execution 业务上下文（contextvars） |
| `app/workers/kafka_worker_main.py` | Kafka Worker 入口 |
| `app/workers/rabbitmq_worker_main.py` | RabbitMQ Worker 入口 |

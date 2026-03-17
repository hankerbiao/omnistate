# Agent 执行任务 API 文档

本文档供 Agent 端开发参考，包含任务下发和数据回调接口。

## 目录

- [1. 任务下发](#1-任务下发)
- [2. 回调接口](#2-回调接口)
  - [2.1 任务消费确认](#21-任务消费确认)
  - [2.2 任务事件上报](#22-任务事件上报)
  - [2.3 用例状态上报](#23-用例状态上报)
  - [2.4 任务完成上报](#24-任务完成上报)

---

## 1. 任务下发

### 接口信息

| 项目 | 内容 |
|------|------|
| 接口地址 | `POST /api/v1/execution/tasks/dispatch` |
| 认证方式 | JWT Token（需 `execution_tasks:write` 权限） |

### 请求参数 (DispatchTaskRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `framework` | string | 是 | 执行框架标识（如 pytest、jest 等） |
| `agent_id` | string | 否 | 目标代理 ID，HTTP 直连模式下必填 |
| `trigger_source` | string | 否 | 触发来源，默认 `manual` |
| `schedule_type` | string | 否 | 调度类型：`IMMEDIATE` / `SCHEDULED`，默认 `IMMEDIATE` |
| `planned_at` | datetime | 否 | 计划执行时间（UTC） |
| `callback_url` | string | 否 | 框架回调地址 |
| `dut` | object | 否 | 被测设备信息，键值对 |
| `cases` | array | 是 | 测试用例列表 |
| `cases[].case_id` | string | 是 | 测试用例业务 ID |

### 请求示例

```json
{
  "framework": "pytest",
  "agent_id": "agent-001",
  "trigger_source": "manual",
  "schedule_type": "IMMEDIATE",
  "callback_url": "https://agent.example.com/callback",
  "dut": {
    "device_name": "test-device-01",
    "platform": "Android",
    "version": "12.0"
  },
  "cases": [
    { "case_id": "TC-001" },
    { "case_id": "TC-002" },
    { "case_id": "TC-003" }
  ]
}
```

### 响应参数 (DispatchTaskResponse)

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID（如 `ET-2026-000001`） |
| `external_task_id` | string | 外部任务 ID（如 `EXT-ET-2026-000001`） |
| `agent_id` | string | 目标代理 ID |
| `dispatch_channel` | string | 下发渠道 |
| `schedule_type` | string | 调度类型 |
| `schedule_status` | string | 调度状态 |
| `dispatch_status` | string | 下发状态 |
| `consume_status` | string | 消费状态 |
| `overall_status` | string | 整体状态 |
| `case_count` | int | 用例数量 |
| `planned_at` | datetime | 计划执行时间 |
| `triggered_at` | datetime | 触发时间 |
| `created_at` | datetime | 创建时间 |

### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "external_task_id": "EXT-ET-2026-000001",
    "agent_id": "agent-001",
    "dispatch_channel": "HTTP",
    "schedule_type": "IMMEDIATE",
    "schedule_status": "PENDING",
    "dispatch_status": "DISPATCHED",
    "consume_status": "UNCONSUMED",
    "overall_status": "RUNNING",
    "case_count": 3,
    "planned_at": null,
    "triggered_at": "2026-03-16T10:00:00Z",
    "created_at": "2026-03-16T09:59:00Z"
  }
}
```

---

## 2. 回调接口

Agent 执行过程中需要回调以下接口上报任务状态。

### 2.1 任务消费确认

确认任务已被 Agent 消费。

#### 接口信息

| 项目 | 内容 |
|------|------|
| 接口地址 | `POST /api/v1/execution/tasks/{task_id}/consume-ack` |
| 认证方式 | JWT Token（需 `execution_tasks:write` 权限） |

#### 请求参数 (ConsumeAckRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `consumer_id` | string | 否 | 消费者标识，默认使用当前用户 ID |

#### 请求示例

```json
{
  "consumer_id": "agent-001"
}
```

#### 响应示例

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "consume_status": "CONSUMED"
  }
}
```

---

### 2.2 任务事件上报

上报任务执行过程中的事件。

#### 接口信息

| 项目 | 内容 |
|------|------|
| 接口地址 | `POST /api/v1/execution/tasks/{task_id}/events` |
| 认证方式 | 无需认证（建议通过内部网络或签名验证） |

#### 请求参数 (ExecutionEventReportRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `event_id` | string | 是 | 事件唯一标识 |
| `event_type` | string | 是 | 事件类型（如 `TEST_START`, `TEST_END`, `ERROR` 等） |
| `seq` | integer | 否 | 事件序号，从 0 开始递增 |
| `source_time` | datetime | 否 | 事件源时间（UTC） |
| `payload` | object | 否 | 原始事件载荷，键值对 |

#### 请求示例

```json
{
  "event_id": "evt-001",
  "event_type": "TEST_START",
  "seq": 0,
  "source_time": "2026-03-16T10:00:00Z",
  "payload": {
    "framework": "pytest",
    "environment": "staging"
  }
}
```

#### 响应参数 (ExecutionEventReportResponse)

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `event_id` | string | 事件 ID |
| `event_type` | string | 事件类型 |
| `seq` | integer | 事件序号 |
| `received_at` | datetime | 接收时间 |
| `processed` | boolean | 是否已处理 |

---

### 2.3 用例状态上报

上报单个用例的执行状态和进度。

#### 接口信息

| 项目 | 内容 |
|------|------|
| 接口地址 | `POST /api/v1/execution/tasks/{task_id}/cases/{case_id}/status` |
| 认证方式 | 无需认证 |

#### 请求参数 (ExecutionCaseStatusReportRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 是 | 用例执行状态（如 `RUNNING`, `PASSED`, `FAILED`, `SKIPPED`） |
| `event_id` | string | 否 | 事件唯一标识 |
| `seq` | integer | 否 | 事件序号 |
| `progress_percent` | float | 否 | 进度百分比（0-100） |
| `step_total` | integer | 否 | 总步数 |
| `step_passed` | integer | 否 | 通过步数 |
| `step_failed` | integer | 否 | 失败步数 |
| `step_skipped` | integer | 否 | 跳过步数 |
| `started_at` | datetime | 否 | 用例开始时间（UTC） |
| `finished_at` | datetime | 否 | 用例结束时间（UTC） |
| `result_data` | object | 否 | 执行结果扩展信息 |

#### 请求示例

```json
{
  "status": "RUNNING",
  "event_id": "evt-002",
  "seq": 1,
  "progress_percent": 50.0,
  "step_total": 10,
  "step_passed": 5,
  "step_failed": 0,
  "step_skipped": 0,
  "started_at": "2026-03-16T10:00:00Z"
}
```

#### 响应参数 (ExecutionCaseStatusReportResponse)

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `case_id` | string | 用例 ID |
| `status` | string | 用例状态 |
| `progress_percent` | float | 进度百分比 |
| `step_total` | integer | 总步数 |
| `step_passed` | integer | 通过步数 |
| `step_failed` | integer | 失败步数 |
| `step_skipped` | integer | 跳过步数 |
| `last_seq` | integer | 最后接收的序号 |
| `accepted` | boolean | 是否接受 |
| `started_at` | datetime | 开始时间 |
| `finished_at` | datetime | 结束时间 |
| `updated_at` | datetime | 更新时间 |

---

### 2.4 任务完成上报

上报任务执行完成，最终状态汇总。

#### 接口信息

| 项目 | 内容 |
|------|------|
| 接口地址 | `POST /api/v1/execution/tasks/{task_id}/complete` |
| 认证方式 | 无需认证 |

#### 请求参数 (ExecutionTaskCompleteRequest)

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 是 | 任务最终状态（如 `PASSED`, `FAILED`, `ERROR`） |
| `event_id` | string | 否 | 完成事件 ID |
| `seq` | integer | 否 | 事件序号 |
| `finished_at` | datetime | 否 | 任务结束时间（UTC） |
| `summary` | object | 否 | 任务结果摘要 |
| `error_message` | string | 否 | 失败原因 |
| `executor` | string | 否 | 执行器标识 |

#### 请求示例

```json
{
  "status": "PASSED",
  "event_id": "evt-010",
  "seq": 10,
  "finished_at": "2026-03-16T10:30:00Z",
  "summary": {
    "total_cases": 3,
    "passed": 3,
    "failed": 0,
    "skipped": 0,
    "duration_seconds": 1800
  },
  "executor": "pytest-runner-v2"
}
```

#### 响应参数 (ExecutionTaskCompleteResponse)

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID |
| `overall_status` | string | 整体状态 |
| `dispatch_status` | string | 下发状态 |
| `consume_status` | string | 消费状态 |
| `reported_case_count` | int | 上报的用例数量 |
| `started_at` | datetime | 开始时间 |
| `finished_at` | datetime | 结束时间 |
| `last_callback_at` | datetime | 最后回调时间 |
| `updated_at` | datetime | 更新时间 |

---

## 附录：通用响应格式

所有接口统一使用以下响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | integer | 状态码，0 表示成功 |
| `message` | string | 消息描述 |
| `data` | object | 响应数据 |

## 附录：状态值参考

| 状态类型 | 可能值 |
|----------|--------|
| `schedule_type` | `IMMEDIATE`, `SCHEDULED` |
| `schedule_status` | `PENDING`, `TRIGGERED`, `CANCELLED` |
| `dispatch_status` | `PENDING`, `DISPATCHED`, `FAILED` |
| `consume_status` | `UNCONSUMED`, `CONSUMED`, `TIMEOUT` |
| `overall_status` | `PENDING`, `RUNNING`, `PASSED`, `FAILED`, `ERROR`, `CANCELLED` |
| `case_status` | `PENDING`, `RUNNING`, `PASSED`, `FAILED`, `SKIPPED`, `ERROR` |

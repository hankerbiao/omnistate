# 测试执行编排

## 1. 概述

`execution` 模块采用“平台主导串行 Case 执行”模型。

基本规则：

- 一个任务可以包含多条测试用例。
- 平台每次只推进当前 1 条 case。
- 执行端回调任务事件、case 状态和最终完成结果。
- 同一个任务支持重试，并保留执行轮次历史。
- 支持“执行完当前 case 后停止”，不会中断当前 case。

## 2. 核心对象

### 2.1 当前态

- `ExecutionTaskDoc`：任务主记录
- `ExecutionTaskCaseDoc`：任务内 case 当前态

### 2.2 历史态

- `ExecutionTaskRunDoc`：任务轮次历史
- `ExecutionTaskRunCaseDoc`：任务轮次内 case 结果
- `ExecutionEventDoc`：原始事件审计

## 3. 执行代理

### 3.1 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/execution/agents/register` | 无 | 注册或刷新执行代理 |
| POST | `/api/v1/execution/agents/{agent_id}/heartbeat` | 无 | 上报代理心跳 |
| GET | `/api/v1/execution/agents` | `execution_agents:read` | 查询代理列表 |
| GET | `/api/v1/execution/agents/{agent_id}` | `execution_agents:read` | 查询代理详情 |

### 3.2 注册字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent_id` | string | 是 | 代理唯一标识 |
| `hostname` | string | 是 | 主机名 |
| `ip` | string | 是 | IP 地址 |
| `port` | int | 否 | 端口 |
| `base_url` | string | 否 | 代理基地址 |
| `region` | string | 是 | 区域 |
| `status` | string | 否 | 默认 `ONLINE` |
| `heartbeat_ttl_seconds` | int | 否 | 默认 90 |

### 3.3 列表查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `region` | string | 按区域过滤 |
| `status` | string | 按状态过滤 |
| `online_only` | bool | 仅返回在线节点 |

### 3.4 调用示例

注册代理：

```http
POST /api/v1/execution/agents/register
Content-Type: application/json

{
  "agent_id": "agent-001",
  "hostname": "test-worker-01",
  "ip": "192.168.1.100",
  "port": 8080,
  "base_url": "http://192.168.1.100:8080",
  "region": "cn-shanghai",
  "heartbeat_ttl_seconds": 90
}
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "agent_id": "agent-001",
    "hostname": "test-worker-01",
    "ip": "192.168.1.100",
    "port": 8080,
    "base_url": "http://192.168.1.100:8080",
    "region": "cn-shanghai",
    "status": "ONLINE",
    "registered_at": "2026-03-17T12:35:00Z",
    "last_heartbeat_at": "2026-03-17T12:35:00Z",
    "heartbeat_ttl_seconds": 90,
    "is_online": true,
    "created_at": "2026-03-17T12:35:00Z",
    "updated_at": "2026-03-17T12:35:00Z"
  }
}
```

查询代理列表：

```http
GET /api/v1/execution/agents?region=cn-shanghai&online_only=true
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "agent_id": "agent-001",
      "hostname": "test-worker-01",
      "ip": "192.168.1.100",
      "port": 8080,
      "base_url": "http://192.168.1.100:8080",
      "region": "cn-shanghai",
      "status": "ONLINE",
      "registered_at": "2026-03-17T12:35:00Z",
      "last_heartbeat_at": "2026-03-17T12:35:30Z",
      "heartbeat_ttl_seconds": 90,
      "is_online": true,
      "created_at": "2026-03-17T12:35:00Z",
      "updated_at": "2026-03-17T12:35:30Z"
    }
  ]
}
```

## 4. 任务下发

### 4.1 接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/execution/tasks/dispatch` | `execution_tasks:write` | 创建并下发任务 |
| POST | `/api/v1/execution/tasks/{task_id}/consume-ack` | `execution_tasks:write` | 确认任务已被消费 |
| POST | `/api/v1/execution/tasks/{task_id}/stop` | `execution_tasks:write` | 执行完当前 case 后停止 |
| POST | `/api/v1/execution/tasks/{task_id}/cancel` | `execution_tasks:write` | 取消未触发定时任务 |
| PUT | `/api/v1/execution/tasks/{task_id}/schedule` | `execution_tasks:write` | 修改未触发定时任务 |
| POST | `/api/v1/execution/tasks/{task_id}/retry` | `execution_tasks:write` | 重试任务 |

### 4.2 下发请求字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `framework` | string | 是 | 执行框架标识 |
| `agent_id` | string | 否 | 指定目标代理 |
| `trigger_source` | string | 否 | 默认 `manual` |
| `schedule_type` | string | 否 | 默认 `IMMEDIATE`，只允许 `IMMEDIATE` 或 `SCHEDULED` |
| `planned_at` | datetime | 否 | 定时执行时间 |
| `callback_url` | string | 否 | 执行端回调地址 |
| `dut` | object | 否 | 被测对象快照 |
| `cases` | object[] | 是 | 执行用例列表 |

`cases` 中每一项只包含：

- `case_id`

### 4.3 请求约束

- `cases` 不能为空。
- `cases` 中 `case_id` 不能重复。
- `schedule_type` 非法时请求直接失败。
- 若 `schedule_type=SCHEDULED`，业务上应提供 `planned_at`。

### 4.4 下发响应字段

`DispatchTaskResponse` 主要包括：

- `task_id`
- `external_task_id`
- `agent_id`
- `dispatch_channel`
- `dedup_key`
- `schedule_type`
- `schedule_status`
- `dispatch_status`
- `consume_status`
- `overall_status`
- `case_count`
- `current_case_id`
- `current_case_index`
- `stop_mode`
- `stop_requested_at`
- `stop_requested_by`
- `stop_reason`
- `planned_at`
- `triggered_at`
- `created_at`

### 4.5 停止语义

`POST /api/v1/execution/tasks/{task_id}/stop` 不是强制中断。

行为如下：

- 当前正在执行的 case 继续跑完。
- 平台收到该 case 终态后，不再下发下一条。
- 任务整体状态进入 `STOPPED`。
- 若任务此时没有正在执行的 case，平台可直接将任务收口为 `STOPPED`。

请求体：

```json
{
  "reason": "用户手动停止，当前 case 结束后停止继续执行"
}
```

## 5. 回调接口

这些接口供执行端上报，不要求业务用户权限。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/execution/tasks/{task_id}/events` | 上报任务事件 |
| POST | `/api/v1/execution/tasks/{task_id}/cases/{case_id}/status` | 上报 case 状态 |
| POST | `/api/v1/execution/tasks/{task_id}/complete` | 上报任务完成结果 |

### 5.1 任务事件上报

请求字段：

- `event_id`
- `event_type`
- `seq`
- `source_time`
- `payload`

### 5.2 Case 状态上报

请求字段：

- `status`
- `event_id`
- `seq`
- `progress_percent`
- `step_total`
- `step_passed`
- `step_failed`
- `step_skipped`
- `started_at`
- `finished_at`
- `result_data`

### 5.3 任务完成上报

请求字段：

- `status`
- `event_id`
- `seq`
- `finished_at`
- `summary`
- `error_message`
- `executor`

## 6. 查询接口

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/v1/execution/tasks` | `execution_tasks:read` | 查询任务列表 |
| GET | `/api/v1/execution/tasks/{task_id}/status` | `execution_tasks:read` | 查询任务当前状态 |
| GET | `/api/v1/execution/tasks/{task_id}/runs` | `execution_tasks:read` | 查询任务历史轮次 |
| GET | `/api/v1/execution/tasks/{task_id}/runs/{run_no}` | `execution_tasks:read` | 查询指定轮次详情 |

### 6.1 任务列表查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `schedule_type` | string | 调度类型 |
| `schedule_status` | string | 调度状态 |
| `dispatch_status` | string | 下发状态 |
| `consume_status` | string | 消费状态 |
| `overall_status` | string | 整体状态 |
| `created_by` | string | 创建人 |
| `agent_id` | string | 目标代理 |
| `framework` | string | 执行框架 |
| `date_from` | datetime | 开始时间 |
| `date_to` | datetime | 结束时间 |
| `limit` | int | 默认 20 |
| `offset` | int | 默认 0 |

## 7. 重试语义

`POST /api/v1/execution/tasks/{task_id}/retry` 的语义不是“只重试单个失败 case”，而是：

- 基于同一个 `task_id` 新建一轮执行
- 重置当前态
- 保留既有历史轮次
- 从第 1 条 case 重新开始串行执行

这也是旧文档中最容易被误解的地方之一。

## 8. 示例

### 8.1 立即执行

```http
POST /api/v1/execution/tasks/dispatch
Authorization: Bearer <token>
Content-Type: application/json

{
  "framework": "pytest",
  "trigger_source": "manual",
  "schedule_type": "IMMEDIATE",
  "dut": {
    "hostname": "server-001",
    "ip": "192.168.1.50"
  },
  "cases": [
    {"case_id": "TC-20260317-0001"},
    {"case_id": "TC-20260317-0002"}
  ]
}
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "external_task_id": "EXT-ET-2026-000001",
    "agent_id": null,
    "dispatch_channel": "KAFKA",
    "dedup_key": "f4c5d9a0",
    "schedule_type": "IMMEDIATE",
    "schedule_status": "TRIGGERED",
    "dispatch_status": "DISPATCHED",
    "consume_status": "PENDING",
    "overall_status": "RUNNING",
    "case_count": 2,
    "current_case_id": "TC-20260317-0001",
    "current_case_index": 0,
    "stop_mode": "NONE",
    "stop_requested_at": null,
    "stop_requested_by": null,
    "stop_reason": null,
    "planned_at": null,
    "triggered_at": "2026-03-17T12:40:00Z",
    "created_at": "2026-03-17T12:40:00Z"
  }
}
```

### 8.2 定时执行

```http
POST /api/v1/execution/tasks/dispatch
Authorization: Bearer <token>
Content-Type: application/json

{
  "framework": "pytest",
  "schedule_type": "SCHEDULED",
  "planned_at": "2026-03-18T09:00:00Z",
  "cases": [
    {"case_id": "TC-20260317-0001"}
  ]
}
```

成功返回示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000002",
    "external_task_id": "EXT-ET-2026-000002",
    "agent_id": null,
    "dispatch_channel": "KAFKA",
    "dedup_key": "c12bb3f8",
    "schedule_type": "SCHEDULED",
    "schedule_status": "PENDING",
    "dispatch_status": "PENDING",
    "consume_status": "PENDING",
    "overall_status": "QUEUED",
    "case_count": 1,
    "current_case_id": "TC-20260317-0001",
    "current_case_index": 0,
    "stop_mode": "NONE",
    "stop_requested_at": null,
    "stop_requested_by": null,
    "stop_reason": null,
    "planned_at": "2026-03-18T09:00:00Z",
    "triggered_at": null,
    "created_at": "2026-03-17T12:42:00Z"
  }
}
```

### 8.3 消费确认

```http
POST /api/v1/execution/tasks/ET-2026-000001/consume-ack
Authorization: Bearer <token>
Content-Type: application/json

{
  "consumer_id": "agent-001"
}
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "consume_status": "ACKED",
    "consumer_id": "agent-001"
  }
}
```

### 8.4 请求执行完当前 case 后停止

```http
POST /api/v1/execution/tasks/ET-2026-000001/stop
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "当前 case 执行完后停止"
}
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "stop_mode": "STOP_AFTER_CURRENT_CASE",
    "stop_requested_at": "2026-03-17T13:02:00Z",
    "stop_requested_by": "admin",
    "stop_reason": "当前 case 执行完后停止",
    "overall_status": "RUNNING",
    "current_case_id": "TC-20260317-0002",
    "current_case_index": 1,
    "updated_at": "2026-03-17T13:02:00Z"
  }
}
```

### 8.5 查询历史轮次

```http
GET /api/v1/execution/tasks/ET-2026-000001/runs
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "task_id": "ET-2026-000001",
      "run_no": 1,
      "trigger_type": "INITIAL",
      "triggered_by": "admin",
      "overall_status": "FAILED",
      "dispatch_status": "COMPLETED",
      "case_count": 2,
      "reported_case_count": 2,
      "stop_mode": "NONE",
      "stop_requested_at": null,
      "stop_requested_by": null,
      "stop_reason": null,
      "started_at": "2026-03-17T12:40:00Z",
      "finished_at": "2026-03-17T12:55:00Z",
      "created_at": "2026-03-17T12:40:00Z",
      "updated_at": "2026-03-17T12:55:00Z"
    },
    {
      "task_id": "ET-2026-000001",
      "run_no": 2,
      "trigger_type": "RETRY",
      "triggered_by": "admin",
      "overall_status": "RUNNING",
      "dispatch_status": "DISPATCHED",
      "case_count": 2,
      "reported_case_count": 1,
      "stop_mode": "STOP_AFTER_CURRENT_CASE",
      "stop_requested_at": "2026-03-17T13:02:00Z",
      "stop_requested_by": "admin",
      "stop_reason": "当前 case 执行完后停止",
      "started_at": "2026-03-17T13:00:00Z",
      "finished_at": null,
      "created_at": "2026-03-17T13:00:00Z",
      "updated_at": "2026-03-17T13:05:00Z"
    }
  ]
}
```

```http
GET /api/v1/execution/tasks/ET-2026-000001/runs/2
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "run_no": 2,
    "trigger_type": "RETRY",
    "triggered_by": "admin",
    "overall_status": "RUNNING",
    "dispatch_status": "DISPATCHED",
    "case_count": 2,
    "reported_case_count": 1,
    "stop_mode": "STOP_AFTER_CURRENT_CASE",
    "stop_requested_at": "2026-03-17T13:02:00Z",
    "stop_requested_by": "admin",
    "stop_reason": "当前 case 执行完后停止",
    "started_at": "2026-03-17T13:00:00Z",
    "finished_at": null,
    "created_at": "2026-03-17T13:00:00Z",
    "updated_at": "2026-03-17T13:05:00Z",
    "dispatch_channel": "KAFKA",
    "dispatch_response": {
      "topic": "execution_tasks"
    },
    "dispatch_error": null,
    "last_callback_at": "2026-03-17T13:05:00Z",
    "cases": [
      {
        "case_id": "TC-20260317-0001",
        "order_no": 0,
        "status": "PASSED",
        "dispatch_status": "COMPLETED",
        "dispatch_attempts": 1,
        "progress_percent": 100,
        "step_total": 5,
        "step_passed": 5,
        "step_failed": 0,
        "step_skipped": 0,
        "started_at": "2026-03-17T13:00:10Z",
        "finished_at": "2026-03-17T13:03:00Z",
        "result_data": {}
      },
      {
        "case_id": "TC-20260317-0002",
        "order_no": 1,
        "status": "RUNNING",
        "dispatch_status": "DISPATCHED",
        "dispatch_attempts": 1,
        "progress_percent": 40,
        "step_total": 5,
        "step_passed": 2,
        "step_failed": 0,
        "step_skipped": 0,
        "started_at": "2026-03-17T13:03:10Z",
        "finished_at": null,
        "result_data": {}
      }
    ]
  }
}
```

### 8.6 任务列表与状态查询示例

```http
GET /api/v1/execution/tasks?overall_status=RUNNING&limit=20&offset=0
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "task_id": "ET-2026-000001",
      "external_task_id": "EXT-ET-2026-000001",
      "framework": "pytest",
      "agent_id": null,
      "dispatch_channel": "KAFKA",
      "dedup_key": "f4c5d9a0",
      "schedule_type": "IMMEDIATE",
      "schedule_status": "TRIGGERED",
      "dispatch_status": "DISPATCHED",
      "consume_status": "ACKED",
      "overall_status": "RUNNING",
      "case_count": 2,
      "latest_run_no": 2,
      "current_run_no": 2,
      "current_case_id": "TC-20260317-0002",
      "current_case_index": 1,
      "stop_mode": "STOP_AFTER_CURRENT_CASE",
      "stop_requested_at": "2026-03-17T13:02:00Z",
      "stop_requested_by": "admin",
      "stop_reason": "当前 case 执行完后停止",
      "planned_at": null,
      "triggered_at": "2026-03-17T12:40:00Z",
      "created_at": "2026-03-17T12:40:00Z",
      "updated_at": "2026-03-17T13:05:00Z"
    }
  ]
}
```

```http
GET /api/v1/execution/tasks/ET-2026-000001/status
Authorization: Bearer <token>
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2026-000001",
    "schedule_status": "TRIGGERED",
    "dispatch_status": "DISPATCHED",
    "consume_status": "ACKED",
    "overall_status": "RUNNING",
    "current_case_id": "TC-20260317-0002",
    "current_case_index": 1,
    "latest_run_no": 2,
    "stop_mode": "STOP_AFTER_CURRENT_CASE",
    "stop_requested_at": "2026-03-17T13:02:00Z",
    "stop_requested_by": "admin",
    "stop_reason": "当前 case 执行完后停止"
  }
}
```

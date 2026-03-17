# 测试执行 API

## 概述

测试执行模块当前覆盖三类能力：

- 执行代理注册与心跳
- 测试任务下发、查询、调度变更
- 执行事件、用例状态、任务完成结果回传

**基础路径**：`/api/v1/execution`

## 权限要求

- `execution_tasks:write`
  - `POST /tasks/dispatch`
  - `POST /tasks/{task_id}/consume-ack`
  - `POST /tasks/{task_id}/cancel`
  - `PUT /tasks/{task_id}/schedule`
  - `POST /tasks/{task_id}/retry`

- `execution_tasks:read`
  - `GET /tasks`
  - `GET /tasks/{task_id}/status`

- `execution_agents:read`
  - `GET /agents`
  - `GET /agents/{agent_id}`

说明：

- 代理注册、代理心跳、执行回传接口当前未挂显式权限依赖。
- 这类接口更适合后续补充专用签名鉴权，而不是直接沿用用户 RBAC。

## 任务下发

### `POST /tasks/dispatch`

请求体核心字段：

```json
{
  "framework": "pytest",
  "agent_id": "agent-sh-01",
  "trigger_source": "manual",
  "schedule_type": "IMMEDIATE",
  "planned_at": "2026-03-17T12:00:00Z",
  "callback_url": "http://agent.local/callback",
  "dut": {
    "asset_id": "DUT-001"
  },
  "cases": [
    { "case_id": "TC-001" },
    { "case_id": "TC-002" }
  ],
  "runtime_config": {
    "retry_failed": true
  }
}
```

说明：

- `agent_id` 在 HTTP 直连模式下很关键。
- `schedule_type` 当前默认 `IMMEDIATE`，也支持定时场景。
- `cases` 当前是只包含 `case_id` 的列表。

成功响应核心字段：

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
- `planned_at`
- `triggered_at`
- `created_at`

## 任务查询与调度

### `GET /tasks`

当前支持的主要查询参数：

- `schedule_type`
- `schedule_status`
- `dispatch_status`
- `consume_status`
- `overall_status`
- `created_by`
- `agent_id`
- `framework`
- `date_from`
- `date_to`
- `limit`
- `offset`

### `GET /tasks/{task_id}/status`

返回任务当前状态快照。

### `POST /tasks/{task_id}/consume-ack`

用于确认任务已经被消费者领取。

请求体：

```json
{
  "consumer_id": "agent-sh-01"
}
```

### `POST /tasks/{task_id}/cancel`

取消尚未触发的定时任务。

### `PUT /tasks/{task_id}/schedule`

修改尚未触发的定时任务，当前可更新：

- `agent_id`
- `planned_at`
- `callback_url`
- `dut`
- `cases`
- `runtime_config`

### `POST /tasks/{task_id}/retry`

重试下发失败的任务。

## 代理接口

### `POST /agents/register`

请求体核心字段：

- `agent_id`
- `hostname`
- `ip`
- `port`
- `base_url`
- `region`
- `status`
- `heartbeat_ttl_seconds`

### `POST /agents/{agent_id}/heartbeat`

请求体：

```json
{
  "status": "ONLINE"
}
```

### `GET /agents`

支持查询参数：

- `region`
- `status`
- `online_only`

### `GET /agents/{agent_id}`

返回单个代理详情和在线状态。

## 执行回传接口

### `POST /tasks/{task_id}/events`

请求体核心字段：

- `event_id`
- `event_type`
- `seq`
- `source_time`
- `payload`

### `POST /tasks/{task_id}/cases/{case_id}/status`

请求体核心字段：

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

### `POST /tasks/{task_id}/complete`

请求体核心字段：

- `status`
- `event_id`
- `seq`
- `finished_at`
- `summary`
- `error_message`
- `executor`

## 维护说明

- 本页只描述当前代码已实现接口。
- 设计背景与演进方向见 `docs/测试执行集成方案.md`。
- 更细的后端实现说明见 `backend/app/modules/execution/README.md`。

# 测试用例下发与执行管理

## 1. 概述

测试用例下发是 DMLV4 系统的核心执行模块，采用**平台主导的串行 Case 执行模式**：

- 一个任务可包含多条测试用例
- 平台只下发当前 1 条 Case
- 外部执行框架只执行当前 Case 并回报结果
- 平台在 Case 终态后自动推进下一条
- 最后一条 Case 完成后自动收口任务

## 2. 执行代理（Execution Agent）

执行代理是实际执行测试用例的 worker 节点。

### 2.1 接口列表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/execution/agents/register` | 无 | 注册或刷新执行代理 |
| POST | `/api/v1/execution/agents/{agent_id}/heartbeat` | 无 | 上报代理心跳 |
| GET | `/api/v1/execution/agents` | `execution_agents:read` | 查询执行代理列表 |
| GET | `/api/v1/execution/agents/{agent_id}` | `execution_agents:read` | 查询执行代理详情 |

### 2.2 字段说明

#### AgentRegisterRequest（注册请求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent_id | string | 是 | 代理唯一标识 |
| hostname | string | 是 | 主机名 |
| ip | string | 是 | 代理 IP |
| port | int | 否 | 代理端口（1-65535） |
| base_url | string | 否 | 代理基地址 |
| region | string | 是 | 区域 |
| status | string | 否 | 代理状态，默认 ONLINE |
| heartbeat_ttl_seconds | int | 否 | 心跳租约秒数，默认 90 |

#### AgentHeartbeatRequest（心跳请求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 代理状态，默认 ONLINE |

#### ExecutionAgentResponse（响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | string | 代理唯一标识 |
| hostname | string | 主机名 |
| ip | string | 代理 IP |
| port | int | 代理端口 |
| base_url | string | 代理基地址 |
| region | string | 区域 |
| status | string | 代理状态 |
| registered_at | datetime | 注册时间 |
| last_heartbeat_at | datetime | 最后心跳时间 |
| heartbeat_ttl_seconds | int | 心跳租约秒数 |
| is_online | bool | 是否在线 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 2.3 注册示例

**注册执行代理**

```http
POST /api/v1/execution/agents/register
Content-Type: application/json

{
  "agent_id": "agent-001",
  "hostname": "test-worker-01",
  "ip": "192.168.1.100",
  "port": 8080,
  "region": "cn-beijing",
  "heartbeat_ttl_seconds": 90
}
```

**响应**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "agent_id": "agent-001",
    "hostname": "test-worker-01",
    "ip": "192.168.1.100",
    "port": 8080,
    "region": "cn-beijing",
    "status": "ONLINE",
    "registered_at": "2024-03-17T10:00:00Z",
    "last_heartbeat_at": "2024-03-17T10:00:00Z",
    "heartbeat_ttl_seconds": 90,
    "is_online": true,
    "created_at": "2024-03-17T10:00:00Z",
    "updated_at": "2024-03-17T10:00:00Z"
  }
}
```

**上报心跳**

```http
POST /api/v1/execution/agents/agent-001/heartbeat
Content-Type: application/json

{
  "status": "ONLINE"
}
```

## 3. 任务下发

### 3.1 接口列表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/v1/execution/tasks/dispatch` | `execution_tasks:write` | 下发测试任务 |
| GET | `/api/v1/execution/tasks` | `execution_tasks:read` | 查询任务列表 |
| GET | `/api/v1/execution/tasks/{task_id}/status` | `execution_tasks:read` | 获取任务状态 |
| POST | `/api/v1/execution/tasks/{task_id}/cancel` | `execution_tasks:write` | 取消未触发的定时任务 |
| PUT | `/api/v1/execution/tasks/{task_id}/schedule` | `execution_tasks:write` | 修改未触发的定时任务 |
| POST | `/api/v1/execution/tasks/{task_id}/retry` | `execution_tasks:write` | 重试失败的任务 |

### 3.2 字段说明

#### DispatchCaseItem（用例项）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| case_id | string | 是 | 测试用例业务 ID |

#### DispatchTaskRequest（任务下发请求）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| framework | string | 是 | 执行框架标识（如 pytest、robot） |
| agent_id | string | 否 | 目标代理 ID，HTTP 直连模式下必填 |
| trigger_source | string | 否 | 触发来源，默认 manual |
| schedule_type | string | 否 | 调度类型，默认 IMMEDIATE，可选值：IMMEDIATE/SCHEDULED |
| planned_at | datetime | 否 | 计划执行时间（UTC），SCHEDULED 模式下必填 |
| callback_url | string | 否 | 框架回调地址 |
| dut | object | 否 | 被测设备信息 |
| cases | object[] | 是 | 测试用例列表，不能为空且不能重复 |

#### DispatchTaskResponse（任务下发响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 任务 ID（如 ET-2024-000001） |
| external_task_id | string | 外部任务 ID |
| agent_id | string | 目标代理 ID |
| dispatch_channel | string | 下发通道 |
| dedup_key | string | 去重键 |
| schedule_type | string | 调度类型 |
| schedule_status | string | 调度状态 |
| dispatch_status | string | 下发状态 |
| consume_status | string | 消费状态 |
| overall_status | string | 整体状态 |
| case_count | int | 用例数量 |
| current_case_id | string | 当前执行的用例 ID |
| current_case_index | int | 当前用例索引 |
| planned_at | datetime | 计划执行时间 |
| triggered_at | datetime | 实际触发时间 |
| created_at | datetime | 创建时间 |

### 3.3 下发示例

**立即执行任务**

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
    "ip": "192.168.1.50",
    "os": "Linux",
    "memory": "256GB"
  },
  "cases": [
    {"case_id": "TC-20240317-0001"},
    {"case_id": "TC-20240317-0002"},
    {"case_id": "TC-20240317-0003"}
  ]
}
```

**响应**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "task_id": "ET-2024-000001",
    "external_task_id": "EXT-ET-2024-000001",
    "agent_id": null,
    "dispatch_channel": "PUSH",
    "schedule_type": "IMMEDIATE",
    "schedule_status": "TRIGGERED",
    "dispatch_status": "DISPATCHED",
    "consume_status": "PENDING",
    "overall_status": "RUNNING",
    "case_count": 3,
    "current_case_id": "TC-20240317-0001",
    "current_case_index": 0,
    "triggered_at": "2024-03-17T10:00:00Z",
    "created_at": "2024-03-17T10:00:00Z"
  }
}
```

**定时任务**

```http
POST /api/v1/execution/tasks/dispatch
Authorization: Bearer <token>
Content-Type: application/json

{
  "framework": "pytest",
  "schedule_type": "SCHEDULED",
  "planned_at": "2024-03-18T09:00:00Z",
  "cases": [
    {"case_id": "TC-20240317-0001"}
  ]
}
```

### 3.4 查询参数

| 参数 | 类型 | 说明 |
|------|------|------|
| schedule_type | string | 按调度类型过滤（IMMEDIATE/SCHEDULED） |
| schedule_status | string | 按调度状态过滤 |
| dispatch_status | string | 按下发状态过滤 |
| consume_status | string | 按消费状态过滤 |
| overall_status | string | 按整体状态过滤 |
| created_by | string | 按创建人过滤 |
| agent_id | string | 按代理 ID 过滤 |
| framework | string | 按执行框架过滤 |
| date_from | datetime | 创建时间起始 |
| date_to | datetime | 创建时间结束 |
| limit | int | 返回数量限制，默认 20 |
| offset | int | 偏移量，默认 0 |

## 4. 任务回调接口

外部执行框架在执行过程中需要回调平台接口，报告执行状态。

### 4.1 确认任务消费

```http
POST /api/v1/execution/tasks/{task_id}/consume-ack
Content-Type: application/json

{
  "consumer_id": "agent-001"
}
```

### 4.2 上报任务事件

```http
POST /api/v1/execution/tasks/{task_id}/events
Content-Type: application/json

{
  "event_id": "evt-001",
  "event_type": "CASE_STARTED",
  "seq": 1,
  "source_time": "2024-03-17T10:05:00Z",
  "payload": {
    "message": "Test case started"
  }
}
```

### 4.3 上报用例执行状态

```http
POST /api/v1/execution/tasks/{task_id}/cases/{case_id}/status
Content-Type: application/json

{
  "status": "RUNNING",
  "event_id": "evt-002",
  "seq": 2,
  "progress_percent": 50.0,
  "step_total": 10,
  "step_passed": 5,
  "step_failed": 0,
  "step_skipped": 5,
  "started_at": "2024-03-17T10:05:00Z"
}
```

**用例状态说明**

| 状态 | 说明 |
|------|------|
| PENDING | 待执行 |
| RUNNING | 执行中 |
| PASSED | 通过 |
| FAILED | 失败 |
| SKIPPED | 跳过 |
| BLOCKED | 阻塞 |

### 4.4 上报任务完成

```http
POST /api/v1/execution/tasks/{task_id}/complete
Content-Type: application/json

{
  "status": "COMPLETED",
  "event_id": "evt-003",
  "seq": 100,
  "finished_at": "2024-03-17T10:30:00Z",
  "summary": {
    "total": 3,
    "passed": 2,
    "failed": 1,
    "skipped": 0
  },
  "executor": "pytest-runner"
}
```

**任务最终状态说明**

| 状态 | 说明 |
|------|------|
| PENDING | 待执行 |
| RUNNING | 执行中 |
| COMPLETED | 全部完成 |
| PARTIAL_FAILED | 部分失败 |
| FAILED | 全部失败 |
| CANCELLED | 已取消 |

## 5. 任务执行历史

### 5.1 查询任务执行历史

```http
GET /api/v1/execution/tasks/{task_id}/runs
Authorization: Bearer <token>
```

### 5.2 查询单次执行结果

```http
GET /api/v1/execution/tasks/{task_id}/runs/{run_no}
Authorization: Bearer <token>
```

## 6. 任务状态流转

### 6.1 状态说明

| 状态类型 | 状态值 | 说明 |
|----------|--------|------|
| schedule_status | PENDING | 待触发 |
| schedule_status | TRIGGERED | 已触发 |
| schedule_status | CANCELLED | 已取消 |
| dispatch_status | PENDING | 待下发 |
| dispatch_status | DISPATCHED | 已下发 |
| dispatch_status | FAILED | 下发失败 |
| consume_status | PENDING | 待消费 |
| consume_status | CONSUMED | 已消费 |
| overall_status | PENDING | 待执行 |
| overall_status | RUNNING | 执行中 |
| overall_status | COMPLETED | 全部通过 |
| overall_status | PARTIAL_FAILED | 部分失败 |
| overall_status | FAILED | 全部失败 |
| overall_status | CANCELLED | 已取消 |

### 6.2 串行执行流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  任务创建   │────▶│  下发 Case1 │────▶│  执行 Case1 │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ Case1 完成? │
                                        └─────────────┘
                              ┌──────────────┴──────────────┐
                              │                              │
                              ▼                              ▼
                       ┌─────────────┐               ┌─────────────┐
                       │   Case2     │               │  任务收口   │
                       │  执行完成   │               │             │
                       └─────────────┘               └─────────────┘
                              │
                              ▼
                       ┌─────────────┐     ┌─────────────┐
                       │  还有Case?  │─Yes─│  下发CaseN  │
                       └─────────────┘     └─────────────┘
                              │
                              No
                              ▼
                       ┌─────────────┐
                       │  任务完成   │
                       └─────────────┘
```

## 7. 统一响应格式

所有接口统一返回以下格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 8. 错误码说明

| code | 说明 |
|------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |

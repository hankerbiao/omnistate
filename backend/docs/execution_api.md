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
| `dispatch_channel` | string | 否 | 下发渠道，支持 `RABBITMQ`、`HTTP` |
| `agent_id` | string | 否 | 目标代理 ID，HTTP 直连模式下必填 |
| `trigger_source` | string | 否 | 触发来源，默认 `manual` |
| `schedule_type` | string | 否 | 调度类型：`IMMEDIATE` / `SCHEDULED`，默认 `IMMEDIATE` |
| `planned_at` | datetime | 否 | 计划执行时间（UTC） |
| `callback_url` | string | 否 | 框架回调地址 |
| `category` | string | 否 | 任务分类 |
| `project_tag` | string | 否 | 项目标记 |
| `repo_url` | string | 否 | 仓库地址 |
| `branch` | string | 否 | 仓库分支 |
| `pytest_options` | object | 否 | pytest 扩展参数 |
| `timeout` | integer | 否 | 任务超时时间，单位秒 |
| `dut` | object | 否 | 被测设备信息，键值对 |
| `cases` | array | 是 | 测试用例列表 |
| `cases[].auto_case_id` | string | 是 | 自动化测试用例业务 ID |
| `cases[].config` | object | 否 | 本次执行的配置快照 |
| `cases[].parameters` | object | 否 | 本次执行传给框架的参数 |

### 请求约束

- 前端请求中的 `cases` 只需要传 `auto_case_id`、`config`、`parameters`
- `script_name`、`script_path`、`script_entity_id` 不再作为前端请求字段
- 后端会基于 `auto_case_id` 从 `automation_test_cases` 解析脚本元数据
- `dispatch` 和 `rerun` 都使用同一套后端解析逻辑
- 实际下发到 RabbitMQ、HTTP 的任务 payload 字段格式不变

### 请求示例

```json
{
  "framework": "pytest",
  "dispatch_channel": "RABBITMQ",
  "agent_id": "agent-001",
  "trigger_source": "manual",
  "schedule_type": "IMMEDIATE",
  "category": "bmc",
  "project_tag": "universal",
  "repo_url": "http://git.example.com/qa/cases.git",
  "branch": "master",
  "pytest_options": {
    "maxfail": "3"
  },
  "timeout": 300,
  "callback_url": "https://agent.example.com/callback",
  "dut": {
    "device_name": "test-device-01",
    "platform": "Android",
    "version": "12.0"
  },
  "cases": [
    {
      "auto_case_id": "ATC-001",
      "config": {
        "target_ip": "10.10.10.100"
      },
      "parameters": {
        "target_ip": "10.10.10.100"
      }
    },
    {
      "auto_case_id": "ATC-002",
      "parameters": {
        "fan_mode": "Manual"
      }
    }
  ]
}
```

### 后端解析后的下发 payload 说明

后端会按 `auto_case_id` 从 `automation_test_cases` 补齐：

- `case_id`
- `script_path`
- `script_name`
- `script_entity_id`

然后再生成实际发送给执行端的任务数据。这个任务数据的字段格式保持不变，例如：

```json
{
  "task_id": "ET-2026-000001",
  "category": "bmc",
  "project_tag": "universal",
  "repo_url": "http://git.example.com/qa/cases.git",
  "branch": "master",
  "cases": [
    {
      "case_id": "TC-2026-00001",
      "script_path": "tests/universal/test_demo.py",
      "script_name": "suite-demo-001",
      "parameters": {
        "target_ip": "10.10.10.100"
      }
    }
  ],
  "pytest_options": {
    "maxfail": "3",
    "task_id": "ET-2026-000001"
  },
  "timeout": 300
}
```

其中：

- Kafka 通道发送 `TaskMessage(task_data=上面的 payload)`
- RabbitMQ 通道发送上面的纯 payload JSON
- HTTP 通道发送上面的纯 payload JSON

### 响应参数 (DispatchTaskResponse)

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID（如 `ET-2026-000001`） |
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

### 重跑说明

`POST /api/v1/execution/tasks/{task_id}/rerun` 在重新生成任务时：

- 仍然沿用原任务里的业务参数和 case 顺序
- 会重新根据 `auto_case_id` 解析当前数据库中的 `script_name`、`script_path`、`script_entity_id`
- 不会改变最终下发给执行端的字段结构

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

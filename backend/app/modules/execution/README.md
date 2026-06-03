# 测试执行模块

`execution` 模块负责测试任务编排。当前实现采用平台串行下发模式：

- 一个任务只执行一次
- 平台一次只向执行端下发当前 1 条 case
- 平台只维护当前任务态和当前 case 态
- 不再提供历史轮次和历史执行结果查询

## 核心模型

### 1. `ExecutionTaskDoc`

任务主表，保存任务当前状态与编排游标。

职责：

- 保存任务身份：`task_id`
- 保存任务配置：`framework`、`agent_id`、`request_payload`
- 保存任务当前态：`schedule_status`、`dispatch_status`、`consume_status`、`overall_status`
- 保存任务聚合统计：`reported_case_count`、`started_case_count`、`finished_case_count`
- 保存串行游标：`current_case_id`、`current_case_index`

### 2. `ExecutionTaskCaseDoc`

任务内 case 当前态表，保存当前任务下每条 case 的即时状态。

职责：

- 保存任务当前使用的 case 列表和顺序
- 保存当前执行状态、进度、断言统计和结果数据
- 作为平台串行推进与前端展示的数据来源

### 3. `ExecutionEventDoc`

执行事件归档表。

职责：

- 基于 `event_id` 做幂等
- 保存原始 Kafka 事件和元数据

### 4. `ExecutionBizLogDoc`

平台侧业务轨迹表（非 Kafka 原始事件）。

职责：

- 记录平台业务节点（创建、下发、事件入库、自动推进、任务完成等）
- 支持按 `task_id` 查询时间线，便于排障

## 日志体系

### 结构化日志

- 共享层：[`app/shared/core/logger.py`](../../shared/core/logger.py) — JSON Lines、`app.log` / `error.log` / `execution.log`
- 模块层：[`shared/execution_log.py`](shared/execution_log.py) — `ExecutionNode` 枚举 + `elog()` API
- 上下文：[`shared/execution_context.py`](shared/execution_context.py) — `task_id` / `case_id` / `event_id` 自动注入

### 业务节点（ExecutionNode）

| 节点 | 含义 |
|------|------|
| `task.create` | 创建任务 |
| `task.dispatch` | 下发 case |
| `event.ingest` | Kafka 事件入库与聚合 |
| `case.update` | case 状态更新 |
| `task.advance` | 自动推进下一条 case |
| `task.complete` | 任务收口完成 |
| `task.delete` / `task.rerun` | 删除 / 重跑 |
| `scheduler.tick` | 定时任务扫描触发 |
| `kafka.batch` / `kafka.result` | Kafka 批量 / 结果消息 |
| `http.dispatch.bg` | HTTP 异步下发后台任务 |

### 排障示例

```bash
# 按 task_id 过滤 execution 域日志
cat logs/execution.log | jq 'select(.task_id=="ET-2026-000001")'

# 按 request_id 关联 HTTP 入口
cat logs/app.log | jq 'select(.request_id=="req_abc123")'

# API 查询业务轨迹
GET /api/v1/execution/tasks/{task_id}/biz-logs
```

### 日志级别约定

- **INFO**：业务节点成功（下发成功、推进下一条、任务完成）
- **WARNING**：可恢复异常（重复 event、case 缺失、下发失败）
- **ERROR**：需人工介入（auto-advance 失败、Kafka batch 单条失败）
- **DEBUG**：payload 预览、状态机 skip 原因

## 执行模型

入口：`POST /api/v1/execution/tasks/dispatch`

流程：

1. 路由生成 `task_id`
2. 基于 `auto_case_id` 从 `automation_test_cases` 解析 `case_id`、`script_entity_id`、`script_path`、`script_name`
3. 校验任务去重键，避免相同业务载荷的未完成任务重复创建
4. 创建 `ExecutionTaskDoc`
5. 创建 `ExecutionTaskCaseDoc`
6. 如果是立即执行，则只下发第 1 条 case

约束：

- 前端请求只负责传 `auto_case_id`、`config`、`parameters`
- 脚本元数据由后端统一解析，不信任前端透传
- `dispatch` 和 `rerun` 都复用同一套解析逻辑
- 最终下发到 RabbitMQ、HTTP 的任务 payload 字段格式保持一致

## application 层结构

- `task_command_service.py`
  负责创建任务、重跑任务、删除任务
- `task_dispatch_service.py`
  负责重建 dispatch command 和真正下发当前 case
- `task_query_service.py`
  负责任务查询和序列化
- `agent_service.py`
  负责代理注册、心跳和查询
- `task_dispatch_mixin.py`
  下发实现细节，供 dispatch service 复用
- `task_case_mixin.py`
  负责 case 解析、快照构建和任务 case 明细维护
- `event_ingest_service.py`
  负责消费 Kafka 事件并回填当前任务态与当前 case 态

## 对外接口

### 任务执行

- `POST /api/v1/execution/tasks/dispatch`
  创建任务并启动执行
- `DELETE /api/v1/execution/tasks/{task_id}`
  删除执行任务（逻辑删除）
- `POST /api/v1/execution/tasks/{task_id}/cancel`
  取消未触发的定时任务
- `POST /api/v1/execution/tasks/{task_id}/stop`
  当前 case 执行完后停止任务

### 查询

- `GET /api/v1/execution/tasks`
  查询任务列表和 case 当前执行情况
- `GET /api/v1/execution/tasks/{task_id}/status`
  查询任务当前状态
- `GET /api/v1/execution/tasks/{task_id}/biz-logs`
  查询任务平台侧业务轨迹日志（排障时间线）

### 代理

- `POST /api/v1/execution/agents/register`
- `POST /api/v1/execution/agents/{agent_id}/heartbeat`
- `GET /api/v1/execution/agents`
- `GET /api/v1/execution/agents/{agent_id}`

## 维护建议

- 改任务创建、删除、取消、停止，优先看 `task_command_service.py`
- 改任务查询返回，优先看 `task_query_mixin.py`
- 改事件消费聚合，优先看 `event_ingest_service.py`
- 改下发通道，优先看 `task_dispatcher.py`

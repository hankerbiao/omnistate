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

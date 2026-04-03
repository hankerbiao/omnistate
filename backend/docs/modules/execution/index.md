# Execution 模块

## 模块职责

`execution` 负责测试任务编排，不是简单的批量下发器。

当前模型是：

- 一个任务包含多条 case
- 平台一次只下发当前 1 条 case
- 外部框架回报事件后，平台更新当前 case 和当前任务态
- case 完成后再决定是否推进下一条

## 核心目录

- `api/routes.py`
  执行任务与 agent 的 HTTP 入口
- `application/task_command_service.py`
  创建、删除、重跑任务
- `application/task_query_service.py`
  查询与序列化
- `application/task_dispatch_service.py`
  负责真实下发
- `application/event_ingest_service.py`
  事件消费和状态回填
- `repository/models/`
  任务、任务 case、事件归档模型

## 核心模型

- `ExecutionTaskDoc`
- `ExecutionTaskCaseDoc`
- `ExecutionEventDoc`

## 关键字段说明

### `ExecutionTaskDoc`

- `task_id`
  执行任务业务 ID
- `framework`
  执行框架标识
- `agent_id`
  目标执行代理 ID
- `request_payload`
  原始任务快照，后续重跑、查询、恢复 case 顺序都依赖它
- `schedule_status`
  调度状态，例如待触发、已就绪
- `dispatch_status`
  分发状态，表示任务是否已真正下发
- `consume_status`
  消费状态，表示平台是否收到执行端回报
- `overall_status`
  任务整体状态，是外部最常见的任务状态字段
- `current_case_id`
  当前正在推进的 case
- `current_case_index`
  当前 case 在任务中的顺序位置

### `ExecutionTaskCaseDoc`

- `task_id`
  所属任务 ID
- `case_id`
  对应平台测试用例 ID
- `order_no`
  该 case 在任务中的顺序
- `status`
  当前 case 状态
- `dispatch_status`
  当前 case 是否已被下发
- `progress_percent`
  当前 case 或任务视角下的进度
- `last_event_id`
  最近一次驱动状态变化的事件 ID
- `result_data`
  当前 case 的展示摘要、断言结果和错误信息

### `ExecutionEventDoc`

- `event_id`
  事件唯一 ID，用于幂等
- `task_id`
  所属任务 ID
- `case_id`
  如果是 case 级事件，则带上对应 case
- `event_type`
  事件类型，例如 progress/assert 等
- `phase`
  事件阶段，例如 `case_start`、`case_finish`
- `processed`
  是否已被平台处理
- `process_error`
  处理失败时记录原因

## 关键调用链

- 下发任务：
  API -> `ExecutionTaskCommandService` -> `ExecutionDispatchService`
- 查询任务：
  API -> `ExecutionTaskQueryService`
- agent 注册与心跳：
  API -> `ExecutionAgentService`
- Kafka/RabbitMQ 事件回填：
  handler -> `ExecutionEventIngestService`

## 关键业务规则

- 任务去重依赖 dedup key
- 请求里的 case 元数据会被后端重新解析，不信任前端透传脚本信息
- 当前态优先，历史执行轮次不是设计重点

## 常见修改场景

- 改任务创建参数：看 `schemas/execution.py` 和 `task_command_service.py`
- 改下发载荷：看 `task_command_mixin.py`、`task_dispatch_service.py`
- 改状态聚合：看 `event_ingest_service.py`

## 风险点

- `execution` 抽象颗粒度偏细，改动前先确定落点，不要在多个 mixin 间来回补丁
- 事件幂等与当前态更新解耦，排查时不要只看 task 表

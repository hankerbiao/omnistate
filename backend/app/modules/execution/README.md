# 测试执行模块

`execution` 模块负责测试任务编排。当前实现不是“整批 case 一次性下发”，而是平台按 case 串行下发，并维护任务当前态与执行过程快照。

当前设计目标：

- 平台主导串行 case 执行
- 外部执行框架只执行当前 1 条 case
- 一个任务只执行一次
- 任务查询以当前态与当前 case 执行情况为主

## 核心模型

### 1. `ExecutionTaskDoc`

任务主表，表示一个稳定的测试任务。

职责：

- 保存任务身份：`task_id`、`external_task_id`
- 保存任务配置：`framework`、`agent_id`、`request_payload`
- 保存当前态：`schedule_status`、`dispatch_status`、`overall_status`
  其中 `schedule_status` 只表示调度生命周期（如 `PENDING/READY/TRIGGERED/CANCELLED`），
  下发成败只放在 `dispatch_status` 和 `overall_status`
- 保存串行游标：`current_case_id`、`current_case_index`
- 保存平台推进锁：`orchestration_lock`

这个表回答的问题是：

- 这个任务现在是什么状态
- 当前执行到哪条 case
- 最近一次是第几轮执行

### 2. `ExecutionTaskCaseDoc`

任务内 case 当前态表。

职责：

- 保存任务当前使用的 case 列表和顺序
- 保存当前一轮执行过程中的实时状态
- 为串行推进提供游标和状态基础

这个表不是历史表，而是编排用的“当前态工作表”。

### 3. `ExecutionTaskRunDoc`

任务执行快照表。

当前仍保留 `run_no` 和快照表，主要用于平台内部事件归档与状态聚合，不再对外提供历史轮次查询能力。

### 4. `ExecutionTaskRunCaseDoc`

任务-case 执行快照表。

当前仍保留该表以便平台内部消费执行事件与聚合状态，但不再暴露“按轮次查看历史结果”的接口。

## 执行模型

### 创建任务

入口：`POST /api/v1/execution/tasks/dispatch`

流程：

1. 路由生成 `task_id` 和 `external_task_id`
2. 构建 `DispatchExecutionTaskCommand`
3. service 校验 case 是否存在
4. 计算 `dedup_key`，阻止相同业务载荷的未完成任务重复创建
5. 创建 `ExecutionTaskDoc`
6. 创建当前态 `ExecutionTaskCaseDoc`
7. 创建首轮执行快照 `ExecutionTaskRunDoc(run_no=1)`
8. 创建首轮 case 快照 `ExecutionTaskRunCaseDoc`
9. 如果是立即执行，则只下发第 1 条 case

## 当前态与历史态的关系

### 当前态

保存在：

- `ExecutionTaskDoc`
- `ExecutionTaskCaseDoc`

用途：

- 串行调度
- 当前任务状态展示
- 平台推进判断

### 执行快照

保存在：

- `ExecutionTaskRunDoc`
- `ExecutionTaskRunCaseDoc`

用途：

- 内部事件归档
- 状态聚合与收口
- 保留执行过程快照

## application 层结构

当前 `application` 采用“门面 + mixin”结构：

- `execution_service.py`
  命令入口，负责创建任务、取消定时任务、真实下发
- `task_status_mixin.py`
  负责任务停止收口和轮次同步
- `task_query_mixin.py`
  负责任务查询和序列化
- `agent_mixin.py`
  负责代理注册、心跳和查询
- `commands.py`
  定义 `DispatchExecutionTaskCommand`
- `constants.py`
  定义任务和 case 终态常量

## 对外接口

### 任务执行

- `POST /api/v1/execution/tasks/dispatch`
  创建任务并启动首轮执行

### 定时任务

- `POST /api/v1/execution/tasks/{task_id}/cancel`
  取消未触发的定时任务

### 查询

- `GET /api/v1/execution/tasks`
  查询任务列表
- `GET /api/v1/execution/tasks/{task_id}/status`
  查询任务当前状态

### 代理

- `POST /api/v1/execution/agents/register`
  注册代理
- `POST /api/v1/execution/agents/{agent_id}/heartbeat`
  上报心跳
- `GET /api/v1/execution/agents`
  查询代理列表
- `GET /api/v1/execution/agents/{agent_id}`
  查询代理详情

## request_payload 与执行快照

`request_payload` 仍然保留在任务主表中，但它的职责很明确：

- 保存任务原始完整快照
- 用于重建命令和继续下发上下文

它不是执行结果表。

## 状态说明

### 任务终态

- `PASSED`
- `FAILED`
- `SKIPPED`
- `CANCELLED`

### case 终态

- `PASSED`
- `FAILED`
- `SKIPPED`

### 常见任务状态

- `QUEUED`
  任务已创建，尚未开始
- `RUNNING`
  当前轮已有 case 开始执行
- `COMPLETED`
  当前轮已完成并收口
- `DISPATCH_FAILED`
  当前下发失败

### 常见调度状态

- `PENDING`
  定时任务尚未到点
- `READY`
  已具备执行条件
- `TRIGGERED`
  已触发真实下发
- `FAILED`
  调度或下发失败
- `CANCELLED`
  已取消

## 当前实现约束

- 所有时间统一使用 UTC
- 任务 ID 格式仍为 `ET-年份-6位序号`
- 外部任务 ID 格式仍为 `EXT-ET-...`
- 当前不依赖 MongoDB 事务
- 去重规则仍然是：相同 `dedup_key` 的未完成任务不能重复创建
- 当前模块不再接收执行端事件回调，任务状态主要反映平台下发侧状态

## 维护建议

- 改任务停止收口与状态同步，优先看 `task_status_mixin.py`
- 改任务创建和定时取消，优先看 `execution_service.py`
- 改任务查询返回，优先看 `task_query_mixin.py`
- 改下发通道，优先看 `task_dispatcher.py`

# 测试执行模块

`execution` 模块负责测试任务编排。当前实现不是“整批 case 一次性下发”，而是平台维护任务和执行历史，按 case 串行下发，并保存同一任务的多次执行结果。

当前设计目标：

- 平台主导串行 case 执行
- 外部执行框架只执行当前 1 条 case
- 同一个任务可以重复执行
- 每次执行都保留独立历史
- 当前态和历史态分开存储，避免完全靠覆盖字段追历史

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
- 保存历史指针：`latest_run_no`、`current_run_no`
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

任务执行轮次表。

每次真正执行一次任务，就生成一条 `run_no` 记录。

职责：

- 标识第几轮执行：`run_no`
- 记录触发方式：`trigger_type`
- 记录触发人：`triggered_by`
- 记录该轮总体结果：`overall_status`
- 记录该轮下发结果：`dispatch_status`、`dispatch_response`、`dispatch_error`
- 记录该轮时间：`started_at`、`finished_at`、`last_callback_at`

### 4. `ExecutionTaskRunCaseDoc`

任务轮次-case 结果表。

职责：

- 保存某个 `task_id + run_no + case_id` 的执行结果
- 保存该 case 在这一轮的状态、进度、步骤统计、结果数据
- 支持查看历史每次 case 的执行结果

### 5. `ExecutionEventDoc`

原始回调事件审计表。

职责：

- 保存外部上报的事件原文
- 作为排障和幂等辅助
- 不承担“历史结果查询模型”的职责

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
7. 创建首轮执行历史 `ExecutionTaskRunDoc(run_no=1)`
8. 创建首轮 case 历史 `ExecutionTaskRunCaseDoc`
9. 如果是立即执行，则只下发第 1 条 case

### 串行推进

平台推进规则：

1. 当前只下发 1 条 case
2. 外部框架回报该 case 的状态
3. 若 case 进入终态 `PASSED/FAILED/SKIPPED`
4. 平台尝试获取 `orchestration_lock`
5. 获取成功后下发下一条 case
6. 没有下一条时，平台自动完成任务

锁的目的很直接：

- 防止同一条 case 的重复回报把下一条下发多次

### 多次执行

当前实现已经支持：

- 一个 `task_id` 可以执行多次
- 每次执行都会新增一个 `run_no`
- 每次执行的 case 结果都会单独保存

也就是说：

- `ExecutionTaskDoc` 是任务容器
- `ExecutionTaskRunDoc` 是第 N 次执行
- `ExecutionTaskRunCaseDoc` 是第 N 次执行中的单条 case 结果

## `/retry` 的真实语义

入口：`POST /api/v1/execution/tasks/{task_id}/retry`

当前不是“只重试当前失败 case”，而是：

- 重新执行整个任务
- 重置当前态 `ExecutionTaskCaseDoc`
- 新建一轮执行历史
- 从第 1 条 case 开始重新串行执行

这条接口更准确的语义其实是“重新执行任务并保留历史轮次”。

## 当前态与历史态的关系

### 当前态

保存在：

- `ExecutionTaskDoc`
- `ExecutionTaskCaseDoc`

用途：

- 串行调度
- 当前任务状态展示
- 平台推进判断

### 历史态

保存在：

- `ExecutionTaskRunDoc`
- `ExecutionTaskRunCaseDoc`

用途：

- 查看某次执行结果
- 查看一个任务的历史执行列表
- 后续扩展结果比对

当前实现仍然会更新任务主表上的最新状态，但历史轮次已经独立持久化，不再只能依赖覆盖字段追历史。

## application 层结构

当前 `application` 采用“门面 + mixin”结构：

- `execution_service.py`
  命令入口，负责创建任务、修改定时任务、重跑任务、真实下发
- `progress_mixin.py`
  负责任务事件、case 状态回报、平台推进、任务收口、轮次同步
- `query_mixin.py`
  负责任务查询、轮次历史查询和序列化
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
- `POST /api/v1/execution/tasks/{task_id}/retry`
  重新执行任务并保留历史轮次

### 定时任务

- `POST /api/v1/execution/tasks/{task_id}/cancel`
  取消未触发的定时任务
- `PUT /api/v1/execution/tasks/{task_id}/schedule`
  修改未触发的定时任务

### 查询

- `GET /api/v1/execution/tasks`
  查询任务列表
- `GET /api/v1/execution/tasks/{task_id}/status`
  查询任务当前状态
- `GET /api/v1/execution/tasks/{task_id}/runs`
  查询任务执行历史
- `GET /api/v1/execution/tasks/{task_id}/runs/{run_no}`
  查询某一轮执行详情

### 代理

- `POST /api/v1/execution/agents/register`
  注册代理
- `POST /api/v1/execution/agents/{agent_id}/heartbeat`
  上报心跳
- `GET /api/v1/execution/agents`
  查询代理列表
- `GET /api/v1/execution/agents/{agent_id}`
  查询代理详情

## 查询能力

当前已经支持两类历史查询：

1. 任务有哪些执行轮次  
通过 `GET /tasks/{task_id}/runs`

2. 某一轮里每条 case 的结果是什么  
通过 `GET /tasks/{task_id}/runs/{run_no}`

这已经能满足：

- 同一个任务多次执行
- 每次结果单独查看
- 追溯某条 case 在不同执行轮次中的表现

当前还没有做专门的“轮次 diff”接口，但数据模型已经具备后续扩展基础。

## 通道适配

`ExecutionTaskDispatcher` 负责选择真实下发通道：

- `kafka`
  构造 `TaskMessage` 投递到 Kafka
- `http`
  调用执行代理 HTTP 接口

外部始终收到的是“当前 1 条 case 的请求”，而不是整批 case。

下发 payload 中会带：

- `task_id`
- `run_no`
- `current_case_id`
- `current_case_index`
- `case_count`

## request_payload 与执行历史

`request_payload` 仍然保留在任务主表中，但它的职责很明确：

- 保存任务原始完整快照
- 用于重建命令和重新执行

它不是历史结果表。

历史结果应查看：

- `ExecutionTaskRunDoc`
- `ExecutionTaskRunCaseDoc`

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
- `/complete` 不允许在 case 未全部终态时提前结束任务
- `/retry` 会重跑整任务，不是只跑失败 case
- 定时任务在未真正触发前，如果被修改，会重建预创建的首轮历史

## 维护建议

- 改串行推进逻辑，优先看 `progress_mixin.py`
- 改任务创建、重跑和定时修改，优先看 `execution_service.py`
- 改任务/轮次查询返回，优先看 `query_mixin.py`
- 改下发通道，优先看 `task_dispatcher.py`
- 如果后续要做历史结果比对接口，建议直接基于 `ExecutionTaskRunCaseDoc` 做，不要再从当前态表反推

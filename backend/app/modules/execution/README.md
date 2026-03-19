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

### 多次执行

当前实现已经支持：

- 一个 `task_id` 可以执行多次
- 每次执行都会新增一个 `run_no`
- 每次执行的 case 结果都会单独保存

也就是说：

- `ExecutionTaskDoc` 是任务容器
- `ExecutionTaskRunDoc` 是第 N 次执行
- `ExecutionTaskRunCaseDoc` 是第 N 次执行中的单条 case 结果

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
  命令入口，负责创建任务、取消定时任务、真实下发
- `progress_mixin.py`
  负责任务停止收口和轮次同步
- `query_mixin.py`
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

## request_payload 与执行历史

`request_payload` 仍然保留在任务主表中，但它的职责很明确：

- 保存任务原始完整快照
- 用于重建命令和继续下发上下文

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
- 当前模块不再接收执行端事件回调，任务状态主要反映平台下发侧状态

## 维护建议

- 改串行推进逻辑，优先看 `progress_mixin.py`
- 改任务创建和定时取消，优先看 `execution_service.py`
- 改任务查询返回，优先看 `query_mixin.py`
- 改下发通道，优先看 `task_dispatcher.py`

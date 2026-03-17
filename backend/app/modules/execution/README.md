# 测试执行模块（execution）

`execution` 模块是 DML V4 中的执行编排层，负责把“一个执行任务包含多条测试用例”的业务请求，转换成“平台逐条下发 case、逐条接收回报、逐条推进、最终自动收口”的执行流程。

当前设计的核心原则是：

- 平台主导串行 case 执行
- 外部执行框架只负责执行当前 1 条 case
- 任务级调度、推进、收口都由平台控制
- 任务状态和 case 状态都持久化到 MongoDB

## 模块职责

- 创建执行任务并生成平台任务号
- 校验测试用例存在性，生成任务主记录和任务-case 明细
- 根据配置通过 Kafka 或 HTTP 下发“当前 case”
- 接收任务事件和 case 状态回报
- 在当前 case 进入终态后自动推进下一条 case
- 在最后一条 case 完成后自动收口任务
- 提供任务查询、定时任务修改、失败重试、消费确认
- 提供执行代理注册、心跳和在线状态查询

## 执行模型

### 1. 任务模型

一个 `ExecutionTaskDoc` 代表一个执行任务，任务内部可包含多条测试用例。

任务层关注：

- 任务标识：`task_id` / `external_task_id`
- 调度状态：`schedule_type` / `schedule_status`
- 下发状态：`dispatch_status`
- 消费状态：`consume_status`
- 总体状态：`overall_status`
- 串行游标：`current_case_id` / `current_case_index`
- 去重键：`dedup_key`
- 编排锁：`orchestration_lock`
- 任务原始快照：`request_payload`
- 最近一次下发响应：`dispatch_response`

### 2. case 模型

一个 `ExecutionTaskCaseDoc` 代表任务中的一条测试用例。

case 层关注：

- 所属任务：`task_id`
- 用例标识：`case_id`
- 顺序：`order_no`
- 下发状态：`dispatch_status`
- 执行状态：`status`
- 执行进度：`progress_percent` / `step_*`
- 时序：`dispatched_at` / `started_at` / `finished_at`
- 幂等字段：`last_seq` / `last_event_id`
- 结果快照：`case_snapshot`

### 3. 平台串行推进

当前不是“整批 case 一次下发”，而是：

1. 创建任务时保存完整 case 列表
2. 平台只下发第 1 条 case
3. 外部执行框架回报该 case 状态
4. 若该 case 进入终态 `PASSED/FAILED/SKIPPED`，平台尝试获取推进锁
5. 获取成功后下发下一条 case
6. 若没有下一条，平台自动收口任务

推进锁通过任务表上的 `orchestration_lock` 控制，目的是避免重复回报或并发回报导致下一条 case 被重复下发。

## 目录结构

- `api/`
  FastAPI 路由层，负责入参与响应。
- `schemas/`
  请求/响应模型和接口级校验。
- `application/`
  执行编排、查询、代理管理和命令对象。
- `service/`
  与外部通道交互的适配层。
- `repository/models/`
  Beanie 文档模型。

## application 层说明

当前 `application` 采用“门面 + mixin”的低风险拆分方式，既降低单类复杂度，又保持 `ExecutionService` 的对外接口稳定。

- `execution_service.py`
  对外门面，保留任务创建、定时修改、重试、真实下发等命令入口。
- `progress_mixin.py`
  处理任务事件、case 状态回报、串行推进和自动收口。
- `query_mixin.py`
  处理任务查询与统一序列化。
- `agent_mixin.py`
  处理代理注册、心跳和代理查询。
- `commands.py`
  定义 `DispatchExecutionTaskCommand`，统一构建下发载荷。
- `constants.py`
  定义终态常量。

## 核心主链路

### 1. 创建任务

入口：`POST /api/v1/execution/tasks/dispatch`

流程：

1. 路由生成 `task_id` 和 `external_task_id`
2. 构造 `DispatchExecutionTaskCommand`
3. 校验请求参数、操作者身份和 case 列表
4. 计算 `dedup_key`，阻止相同业务载荷的未完成任务重复创建
5. 创建 `ExecutionTaskDoc`
6. 创建全部 `ExecutionTaskCaseDoc`
7. 如果是立即执行任务，则只下发第 1 条 case
8. 如果是定时任务且尚未到时间，则只保存任务，不立即下发

### 2. 执行回报

入口：

- `POST /api/v1/execution/tasks/{task_id}/events`
- `POST /api/v1/execution/tasks/{task_id}/cases/{case_id}/status`

平台处理逻辑：

- 记录原始事件审计
- 更新 case 执行状态和进度
- 更新任务级统计和最后回调时间
- 对终态 case 执行“推进下一条 or 自动收口”

### 3. 任务完成

入口：`POST /api/v1/execution/tasks/{task_id}/complete`

当前语义：

- 不是给外部框架提前结束任务用的
- 只有当所有 case 都已进入终态时，才允许调用该接口收口任务
- 平台仍然是任务完成状态的最终控制者

## 通道适配

`ExecutionTaskDispatcher` 负责根据配置选择下发通道：

- `kafka`
  将当前 case 封装为 `TaskMessage` 投递到 Kafka
- `http`
  调用代理的 `base_url + EXECUTION_AGENT_DISPATCH_PATH`

无论哪种通道，外部拿到的都是“当前 1 条 case 的执行请求”，不是完整任务批量请求。

## request_payload 与 dispatch_response

这两个字段的职责不同：

- `request_payload`
  保存任务级原始完整快照，包括全部 `cases`
- `dispatch_response`
  保存最近一次真实下发的响应结果

这意味着：

- `request_payload` 用于重试、重建命令、恢复上下文
- `dispatch_response` 用于记录最近一次通道响应或消费确认信息

## 关键状态说明

### 任务终态

- `PASSED`
- `FAILED`
- `SKIPPED`
- `CANCELLED`

### case 终态

- `PASSED`
- `FAILED`
- `SKIPPED`

### 常见任务状态流转

- `QUEUED`
  任务已创建，尚未开始执行
- `RUNNING`
  已有 case 开始执行
- `COMPLETED`
  所有 case 已完成，且任务已收口
- `DISPATCH_FAILED`
  当前 case 下发失败

### 常见调度状态

- `PENDING`
  定时任务尚未到执行时间
- `READY`
  可触发下发
- `TRIGGERED`
  已触发真实下发
- `FAILED`
  下发阶段失败
- `CANCELLED`
  被取消

## API 概览

- `POST /api/v1/execution/tasks/dispatch`
  创建执行任务
- `POST /api/v1/execution/tasks/{task_id}/events`
  接收任务事件
- `POST /api/v1/execution/tasks/{task_id}/cases/{case_id}/status`
  接收 case 状态和进度
- `POST /api/v1/execution/tasks/{task_id}/complete`
  收口任务
- `POST /api/v1/execution/tasks/{task_id}/consume-ack`
  标记任务已被消费者消费
- `GET /api/v1/execution/tasks`
  查询任务列表
- `GET /api/v1/execution/tasks/{task_id}/status`
  查询任务详情
- `POST /api/v1/execution/tasks/{task_id}/cancel`
  取消未触发的定时任务
- `PUT /api/v1/execution/tasks/{task_id}/schedule`
  修改未触发的定时任务
- `POST /api/v1/execution/tasks/{task_id}/retry`
  重试失败任务
- `POST /api/v1/execution/agents/register`
  注册代理
- `POST /api/v1/execution/agents/{agent_id}/heartbeat`
  上报代理心跳
- `GET /api/v1/execution/agents`
  查询代理列表
- `GET /api/v1/execution/agents/{agent_id}`
  查询代理详情

## 权限要求

- `execution_tasks:write`
  创建任务、修改定时任务、取消、重试、消费确认
- `execution_tasks:read`
  查询任务列表和详情
- `execution_agents:read`
  查询代理列表和详情

## 依赖关系

- 依赖 `test_specs` 模块校验 `TestCaseDoc`
- 依赖 `shared.service.SequenceIdService` 生成任务流水号
- 依赖 `shared.infrastructure` 中的 Kafka 基础设施注册表（仅 Kafka 模式）
- 依赖 `shared.core.mongo_client` 做原子推进锁控制

## 当前实现约束

- 所有时间字段统一使用 UTC
- 任务 ID 格式为 `ET-年份-6位序号`
- 外部任务 ID 格式为 `EXT-ET-...`
- 当前不依赖 MongoDB 事务
- 去重规则是：相同 `dedup_key` 的未完成任务不能重复创建
- HTTP 模式下必须显式传 `agent_id`
- `/complete` 不允许在 case 未全部终态时提前结束任务

## 维护建议

- 新增执行策略时，优先修改 `progress_mixin.py`，不要把推进逻辑散回路由层
- 新增任务返回字段时，优先更新 `query_mixin.py` 中的统一序列化
- 新增通道时，优先扩展 `task_dispatcher.py`，保持 `ExecutionService` 不感知通道细节
- 若后续继续演进，可把 mixin 进一步替换为独立 service 类；当前 mixin 是保持兼容的过渡结构

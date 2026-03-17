# 测试执行模块（execution）

本模块负责 **测试执行任务的创建、分发、串行推进、代理注册与状态查询**，对应架构中的“执行层”。
当前实现由 **平台主导串行 case 执行**：一个任务可包含多条测试用例，但平台每次只向外部框架下发当前 1 条 case；上一条进入终态并完成回报后，平台才推进下一条。

## 主要职责
- 接收执行任务下发请求并生成平台任务 ID
- 校验测试用例是否存在，写入任务主记录与任务明细
- 根据配置选择 Kafka 或 HTTP 通道，下发当前 1 条 case
- 接收 case 回报并在平台内推进下一条 case
- 在存在同业务载荷且未完成任务时阻止重复下发
- 提供任务状态查询、定时任务修改与失败重试能力
- 提供执行代理注册、心跳和在线状态查询能力
- 保存任务与 case 级执行事件审计

## 目录结构
- `api/`：HTTP 路由层（FastAPI）
- `schemas/`：API 请求/响应模型
- `application/`：执行服务与请求命令对象
- `service/`：执行分发器与通道适配
- `repository/models/`：Beanie 文档模型

## 核心模型
- `ExecutionTaskDoc`：执行任务主表，记录下发状态、总体状态、请求快照与响应信息
- `ExecutionTaskCaseDoc`：任务下的用例明细，保存用例快照与逐条执行状态
- `ExecutionEventDoc`：执行事件审计表，用于保存回调事件与处理结果
- `ExecutionAgentDoc`：执行代理注册表，保存代理地址信息与心跳租约
- `DispatchExecutionTaskCommand`：任务下发命令对象，统一构建并校验 Kafka 任务载荷
- `ExecutionTaskDispatcher`：根据配置选择 Kafka 或 HTTP 直连代理进行下发

## 当前架构
- `ExecutionService`：对外兼容门面，负责任务创建、定时修改、重试与真实下发
- `ExecutionProgressMixin`：处理 task event、case status、平台推进与自动收口
- `ExecutionTaskQueryMixin`：处理任务查询与统一序列化
- `ExecutionAgentMixin`：处理代理注册、心跳和查询
- 外部框架：仅负责执行当前 case 并回报结果，不参与任务级调度或完成判定

## 当前主链路
1. 客户端调用 `POST /api/v1/execution/tasks/dispatch` 提交任务下发请求。
2. 路由生成 `task_id` / `external_task_id`，并构造 `DispatchExecutionTaskCommand`；HTTP 模式下请求需显式传 `agent_id`。
3. `ExecutionService` 校验命令、校验测试用例存在性，并检查操作者身份。
4. 服务写入 `ExecutionTaskDoc` 与 `ExecutionTaskCaseDoc`。
5. 平台只下发首条 case；`ExecutionTaskDispatcher` 根据 `EXECUTION_DISPATCH_MODE` 选择 Kafka 或 HTTP 通道执行下发。
6. 外部框架回报 `POST /tasks/{task_id}/cases/{case_id}/status` 后，平台更新当前 case 状态。
7. 若该 case 已终态，平台获取推进锁并自动下发下一条 case。
8. 最后一条 case 完成后，平台自动将任务收口为最终状态。

## API 概览
- `POST /api/v1/execution/agents/register`：注册或刷新代理基础信息
- `POST /api/v1/execution/agents/{agent_id}/heartbeat`：上报代理心跳
- `GET /api/v1/execution/agents`：查询代理列表
- `GET /api/v1/execution/agents/{agent_id}`：查询代理详情
- `POST /api/v1/execution/tasks/dispatch`：下发测试任务
- `POST /api/v1/execution/tasks/{task_id}/events`：接收任务事件上报
- `POST /api/v1/execution/tasks/{task_id}/cases/{case_id}/status`：接收用例状态/进度上报
- `POST /api/v1/execution/tasks/{task_id}/complete`：接收任务最终完成结果
- `POST /api/v1/execution/tasks/{task_id}/consume-ack`：确认任务已被消费者消费
- `GET /api/v1/execution/tasks`：查询执行任务列表
- `GET /api/v1/execution/tasks/{task_id}/status`：查询任务状态
- `POST /api/v1/execution/tasks/{task_id}/cancel`：取消未触发的定时任务
- `PUT /api/v1/execution/tasks/{task_id}/schedule`：修改未触发的定时任务
- `POST /api/v1/execution/tasks/{task_id}/retry`：重试下发失败的任务

路由定义位于 `api/routes.py`，权限要求如下：
- `execution_agents:read`：查询代理列表与详情
- `execution_tasks:write`：下发任务、重试任务
- `execution_tasks:read`：查询任务状态

## 分层说明
- `application/execution_service.py`
  负责对外兼容门面，保留任务命令入口。
- `application/progress_mixin.py`
  负责平台主导的串行 case 推进、事件处理与任务自动收口。
- `application/query_mixin.py`
  负责任务查询与统一序列化。
- `application/agent_mixin.py`
  负责代理注册、心跳和查询。
- `service/task_dispatcher.py`
  负责具体下发通道选择与适配。

## 依赖关系
- 依赖 `test_specs` 模块校验 `TestCaseDoc` 是否存在
- 依赖 `shared.infrastructure` 中的 Kafka 基础设施注册表（仅 `kafka` 模式）
- 依赖 `shared.service.SequenceIdService` 生成任务流水号

## 备注
- 所有时间字段统一使用 UTC。
- 任务 ID 格式为 `ET-年份-6位序号`，外部任务 ID 格式为 `EXT-ET-...`。
- 当前实现不依赖 MongoDB 事务能力。
- 代理查询结果会基于 `last_heartbeat_at + heartbeat_ttl_seconds` 推导在线状态，超时心跳会自动视为 `OFFLINE`。
- 执行任务会生成 `dedup_key`；当存在同 `dedup_key` 且任务尚未完成时，系统会拒绝重复下发。
- `EXECUTION_DISPATCH_MODE=http` 时，系统会通过代理的 `base_url + EXECUTION_AGENT_DISPATCH_PATH` 进行异步 HTTP 下发，请求必须显式传 `agent_id`。
- `/tasks/{task_id}/complete` 不再允许外部框架提前结束任务；只有所有 case 都已到终态时才允许收口。

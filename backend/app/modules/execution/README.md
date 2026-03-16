# 测试执行模块（execution）

本模块负责 **测试执行任务的创建、分发、代理注册与状态查询**，对应架构中的“执行层”。
当前实现通过 **统一任务分发器** 下发任务，可通过配置选择 **Kafka 发布** 或 **HTTP 直连代理**。

## 主要职责
- 接收执行任务下发请求并生成平台任务 ID
- 校验测试用例是否存在，写入任务主记录与任务明细
- 根据配置选择 Kafka 或 HTTP 通道下发任务，并记录成功或失败结果
- 在消费者确认消费前阻止同业务命令重复下发
- 提供任务状态查询与失败重试能力
- 提供执行代理注册、心跳和在线状态查询能力
- 为执行回调与审计预留执行事件模型

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

## 当前主链路
1. 客户端调用 `POST /api/v1/execution/tasks/dispatch` 提交任务下发请求。
2. 路由生成 `task_id` / `external_task_id`，并构造 `DispatchExecutionTaskCommand`；HTTP 模式下请求需显式传 `agent_id`。
3. `ExecutionService` 校验命令、校验测试用例存在性，并检查操作者身份。
4. 服务写入 `ExecutionTaskDoc` 与 `ExecutionTaskCaseDoc`。
5. `ExecutionTaskDispatcher` 根据 `EXECUTION_DISPATCH_MODE` 选择 Kafka 或 HTTP 通道执行下发。
6. 根据发送结果更新 `dispatch_status`、`dispatch_channel` 和错误信息。
7. 消费者领取消息后通过 ack 接口将 `consume_status` 更新为 `CONSUMED`。

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
  负责当前唯一写操作入口，包含任务下发与代理注册/心跳逻辑。
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
- 执行任务会生成 `dedup_key`；当存在同 `dedup_key` 且 `consume_status=PENDING` 的任务时，系统会拒绝重复下发。
- `EXECUTION_DISPATCH_MODE=http` 时，系统会通过代理的 `base_url + EXECUTION_AGENT_DISPATCH_PATH` 进行异步 HTTP 下发，请求必须显式传 `agent_id`。

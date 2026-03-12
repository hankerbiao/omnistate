# 测试执行模块（execution）

本模块负责 **测试执行任务的创建、分发与状态查询**，对应架构中的“执行层”。
当前实现以 **显式命令 + Outbox 模式 + Kafka 发布** 为唯一写链路，用于将测试任务可靠地下发到外部执行框架。

## 主要职责
- 接收执行任务下发请求并生成平台任务 ID
- 校验测试用例是否存在，写入任务主记录与任务明细
- 在同一事务内创建 outbox 事件，解耦本地写库与外部 Kafka 发布
- 提供任务状态查询与失败重试能力
- 为执行回调与审计预留执行事件模型

## 目录结构
- `api/`：HTTP 路由层（FastAPI）
- `schemas/`：API 请求/响应模型
- `application/`：显式命令对象与命令服务
- `repository/models/`：Beanie 文档模型
- `infrastructure/`：Kafka 发布器与 Outbox 后台工作器

## 核心模型
- `ExecutionTaskDoc`：执行任务主表，记录下发状态、总体状态、请求快照与响应信息
- `ExecutionTaskCaseDoc`：任务下的用例明细，保存用例快照与逐条执行状态
- `ExecutionEventDoc`：执行事件审计表，用于保存回调事件与处理结果
- `DispatchExecutionTaskCommand`：任务下发命令对象，统一构建并校验 Kafka 任务载荷

## 当前主链路
1. 客户端调用 `POST /api/v1/execution/tasks/dispatch` 提交任务下发请求。
2. 路由生成 `task_id` / `external_task_id`，并构造 `DispatchExecutionTaskCommand`。
3. `ExecutionCommandService` 校验命令、校验测试用例存在性，并检查操作者身份。
4. 服务在单个 MongoDB 事务内写入：
   - `ExecutionTaskDoc`
   - `ExecutionTaskCaseDoc`
   - outbox 事件
5. API 立即返回“已创建、待分发”结果，不阻塞等待 Kafka。
6. `OutboxWorker` 轮询待发送事件，通过 `KafkaTaskPublisher` 发布到 Kafka。
7. 发布成功后更新 outbox 状态；失败则按重试策略继续处理。

## API 概览
- `POST /api/v1/execution/tasks/dispatch`：下发测试任务
- `GET /api/v1/execution/tasks/{task_id}/status`：查询任务状态
- `POST /api/v1/execution/tasks/{task_id}/retry`：重试下发失败的任务

路由定义位于 `api/routes.py`，权限要求如下：
- `execution_tasks:write`：下发任务、重试任务
- `execution_tasks:read`：查询任务状态

## 分层说明
- `application/execution_command_service.py`
  负责当前推荐的写操作入口，核心特点是“事务内写库 + outbox 异步发布”。
- `infrastructure/outbox_worker.py`
  后台轮询 outbox 事件，负责真正的外部发布。
- `infrastructure/kafka_task_publisher.py`
  封装 execution task 到 Kafka 的消息发布细节。

## 依赖关系
- 依赖 `test_specs` 模块校验 `TestCaseDoc` 是否存在
- 依赖 `shared.integration.outbox_service` 创建和消费 outbox 事件
- 依赖 `shared.infrastructure` 中的 Kafka 基础设施注册表
- 依赖 `shared.service.SequenceIdService` 生成任务流水号

## 备注
- 所有时间字段统一使用 UTC。
- 任务 ID 格式为 `ET-年份-6位序号`，外部任务 ID 格式为 `EXT-ET-...`。
- `ExecutionCommandService` 依赖 MongoDB 事务能力；若部署不是 replica set，会拒绝任务分发。

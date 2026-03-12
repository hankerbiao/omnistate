# 测试执行模块（execution）

本模块负责 **测试执行任务的创建、分发与状态查询**，对应架构中的“执行层”。
当前实现以 **简单服务 + 直接 Kafka 发布** 为唯一写链路，保持实现简单直接。

## 主要职责
- 接收执行任务下发请求并生成平台任务 ID
- 校验测试用例是否存在，写入任务主记录与任务明细
- 直接尝试将任务下发到 Kafka，并记录成功或失败结果
- 提供任务状态查询与失败重试能力
- 为执行回调与审计预留执行事件模型

## 目录结构
- `api/`：HTTP 路由层（FastAPI）
- `schemas/`：API 请求/响应模型
- `application/`：执行服务与请求命令对象
- `repository/models/`：Beanie 文档模型

## 核心模型
- `ExecutionTaskDoc`：执行任务主表，记录下发状态、总体状态、请求快照与响应信息
- `ExecutionTaskCaseDoc`：任务下的用例明细，保存用例快照与逐条执行状态
- `ExecutionEventDoc`：执行事件审计表，用于保存回调事件与处理结果
- `DispatchExecutionTaskCommand`：任务下发命令对象，统一构建并校验 Kafka 任务载荷

## 当前主链路
1. 客户端调用 `POST /api/v1/execution/tasks/dispatch` 提交任务下发请求。
2. 路由生成 `task_id` / `external_task_id`，并构造 `DispatchExecutionTaskCommand`。
3. `ExecutionService` 校验命令、校验测试用例存在性，并检查操作者身份。
4. 服务写入 `ExecutionTaskDoc` 与 `ExecutionTaskCaseDoc`。
5. 服务直接调用 Kafka 管理器发送任务。
6. 根据发送结果更新 `dispatch_status` 和错误信息。

## API 概览
- `POST /api/v1/execution/tasks/dispatch`：下发测试任务
- `GET /api/v1/execution/tasks/{task_id}/status`：查询任务状态
- `POST /api/v1/execution/tasks/{task_id}/retry`：重试下发失败的任务

路由定义位于 `api/routes.py`，权限要求如下：
- `execution_tasks:write`：下发任务、重试任务
- `execution_tasks:read`：查询任务状态

## 分层说明
- `application/execution_service.py`
  负责当前唯一写操作入口，校验命令、持久化任务并直接发送 Kafka。

## 依赖关系
- 依赖 `test_specs` 模块校验 `TestCaseDoc` 是否存在
- 依赖 `shared.infrastructure` 中的 Kafka 基础设施注册表
- 依赖 `shared.service.SequenceIdService` 生成任务流水号

## 备注
- 所有时间字段统一使用 UTC。
- 任务 ID 格式为 `ET-年份-6位序号`，外部任务 ID 格式为 `EXT-ET-...`。
- 当前实现不依赖 MongoDB 事务能力。

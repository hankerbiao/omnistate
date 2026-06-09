# 执行计划模块（execution_plan）

管理手工执行计划和执行任务，支持计划创建、条目分发、结果回填和归档。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — API 请求/响应模型
- `service/` — 执行计划领域服务
- `repository/models/` — Beanie 文档模型

## 核心模型

- `ExecutionPlanDoc` — 执行计划
- `ExecutionPlanItemDoc` — 执行计划条目

## API 前缀

- `/api/v1/execution-plans`

## 核心依赖

- `test_specs` — 读取测试用例和自动化用例配置

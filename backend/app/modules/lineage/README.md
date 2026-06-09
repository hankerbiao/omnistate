# 血缘关系模块（lineage）

提供需求、测试用例、执行任务之间的血缘关系追溯，帮助理解测试资产的依赖链路。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — API 请求/响应模型
- `service/` — 血缘关系查询服务
- `domain/` — 领域异常

## API 前缀

- `/api/v1/lineage`

## 核心依赖

- `workflow` — 读取工作流事项状态
- `test_specs` — 读取需求和测试用例
- `execution` — 读取执行任务

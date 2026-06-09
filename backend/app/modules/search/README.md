# 搜索模块（search）

全文搜索引擎，支持对测试需求、测试用例等工作项进行跨模块统一搜索。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — API 请求/响应模型
- `service/` — 搜索服务

## API 前缀

- `/api/v1/search`

## 核心依赖

- `test_specs` — 搜索需求和测试用例
- `workflow` — 搜索工作流事项

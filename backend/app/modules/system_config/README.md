# 系统配置模块（system_config）

管理应用全局配置项，支持配置的 CRUD、批量更新、加密存储、变更历史追溯，以及 AI 连接测试。

## 目录结构

- `api/` — HTTP 路由（含 AI 连接测试路由 `ai_routes.py`）
- `schemas/` — API 请求/响应模型
- `service/` — 系统配置服务
- `repository/models/` — Beanie 文档模型

## 核心模型

- `SystemConfigDoc` — 系统配置文档
- `SystemConfigHistoryDoc` — 配置变更历史

## API 前缀

- `/api/v1/system-configs` — 配置管理
- `/api/v1/system-configs/ai/test-connection` — AI 连接测试

## 说明

- 配置项支持 `string`/`integer`/`float`/`boolean`/`json` 五种类型
- 敏感值（如 API key）标记为 `is_encrypted`，不会明文返回给前端
- 启动时自动初始化默认配置（仅创建缺失项）

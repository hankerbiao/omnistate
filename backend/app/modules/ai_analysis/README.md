# AI 分析模块（ai_analysis）

提供基于 AI 的测试资产分析能力，包括用例集质量评估、冗余检测和覆盖度分析。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — 请求/响应模型
- `service/` — AI 分析服务逻辑

## API 前缀

- `/api/v1/ai-analyze` — 分析入口

## 核心依赖

- `system_config` — 读取 AI 配置（base_url、model、api_key 等）

# 失败分析模块（failure_analysis）

对执行任务中的失败用例进行智能分析，提供失败模式分类、根因分析和趋势统计。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — API 请求/响应模型
- `service/` — 失败分析服务及模式分类器
- `domain/` — 领域异常

## API 前缀

- `/api/v1/failure-analysis`

## 核心依赖

- `execution` — 读取执行任务和用例数据

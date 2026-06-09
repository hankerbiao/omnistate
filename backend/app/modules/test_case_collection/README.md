# 测试用例集合模块（test_case_collection）

管理预制用例集（TestCaseCollection），支持将多个测试用例聚合为可复用的集合，用于批量执行和分发。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — API 请求/响应模型
- `service/` — 集合管理服务
- `repository/models/` — Beanie 文档模型

## 核心模型

- `TestCaseCollectionDoc` — 测试用例集合

## API 前缀

- `/api/v1/test-case-collections`

## 核心依赖

- `test_specs` — 引用测试用例和自动化用例

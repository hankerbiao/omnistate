# 测试规格模块（test_specs）

本模块负责 **测试需求与测试用例的定义与管理**，对应架构中的“需求与用例定义层”。
它提供需求与用例的数据模型、服务逻辑，以及 API 路由。

## 主要职责
- 管理测试需求（Test_Requirement）
- 管理测试用例（Test_Case）
- 维护需求与用例的关联关系（方案 A：单向父子）
- 提供 CRUD 接口与查询能力

## 目录结构
- `api/`：HTTP 路由层（FastAPI）
- `schemas/`：API 请求/响应模型
- `service/`：领域服务逻辑
- `repository/models/`：Beanie 文档模型与 Pydantic 模型

## 核心模型
- `TestRequirementDoc`：测试需求
- `TestCaseDoc`：测试用例（包含 `ref_req_id` 字段）
- `AutomationTestCaseDoc`：自动化测试用例库（支持 `auto_case_id + version`）

## 需求与用例关系（方案 A）
- 一对多：一个需求对应多个用例
- 用例只归属一个需求
- 关联字段：`Test_Case.ref_req_id`

## API 概览
- 需求：`/api/v1/requirements`
- 用例：`/api/v1/test-cases`
- 自动化用例库：`/api/v1/automation-test-cases`
- 自动化框架元数据上报：`POST /api/v1/automation-test-cases/report`
- 用例关联自动化：`/api/v1/test-cases/{case_id}/automation-link`

## 备注
- 创建或更新用例时会校验 `ref_req_id` 是否存在。
- 自动化用例库当前已提供创建接口：`POST /api/v1/automation-test-cases`
- 自动化框架可直接上报单条用例配置元数据，后端会原样保存到 `metadata_payload` 字段。
- 所有时间字段统一使用 UTC。

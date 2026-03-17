# 测试需求与测试用例关联关系设计（方案 A：单向父子关系）

更新时间：2026-03-03

## 文档边界

- 本文档描述 `test_specs` 模块中“需求-用例”关系的后端落地约束。
- 产品级字段定义与业务背景请参考：
  - `../测试对象与字段规范.md`
  - `../测试设计与BOM关联方案.md`
- 后端统一响应规范请参考：`../接口与认证说明.md`

## 1. 目标与原则

- 显式溯源：需求驱动用例，保证需求到用例的单向追溯。
- 简单可落地：优先采用一对多模型，降低实现和维护复杂度。
- 查询高效：需求下用例查询为核心路径，按 `ref_req_id` 直接检索。

## 2. 关系定义

- 一对多：一个测试需求（`Test_Requirement`）可关联多个测试用例（`Test_Case`）。
- 单向父子：一个测试用例只归属一个需求。
- 关联字段：在 `Test_Case` 中维护 `ref_req_id`。

```text
Test_Requirement (req_id) 1 ---- n Test_Case (ref_req_id)
```

## 3. 后端落地范围

模块路径：`backend/app/modules/test_specs/`

- 需求路由：`/api/v1/requirements`
- 用例路由：`/api/v1/test-cases`
- 核心关系：`TestCase.ref_req_id -> Requirement.req_id`

## 4. 数据模型字段

### 4.1 Test_Requirement

- `req_id`：需求唯一编号（业务主键）
- 其他字段保持既有设计

### 4.2 Test_Case

- `ref_req_id: String`（必填）
- 指向 `Test_Requirement.req_id`

## 5. 业务规则（当前实现）

1. 创建用例时必须校验 `ref_req_id` 对应需求存在。
2. 更新用例时若修改 `ref_req_id`，必须再次校验需求存在。
3. 支持按 `ref_req_id` 查询用例列表。
4. 删除需求时应避免悬挂用例（由服务层策略控制：拦截或级联）。

## 6. 接口映射

### 6.1 需求

- `POST /api/v1/requirements`
- `GET /api/v1/requirements`
- `GET /api/v1/requirements/{req_id}`
- `PUT /api/v1/requirements/{req_id}`
- `DELETE /api/v1/requirements/{req_id}`

### 6.2 用例

- `POST /api/v1/test-cases`
- `GET /api/v1/test-cases`
- `GET /api/v1/test-cases/{case_id}`
- `PUT /api/v1/test-cases/{case_id}`
- `DELETE /api/v1/test-cases/{case_id}`

示例查询：

```http
GET /api/v1/test-cases?ref_req_id=TR-2026-001
```

## 7. 权限要求

- 需求接口：`requirements:read` / `requirements:write`
- 用例接口：`test_cases:read` / `test_cases:write`

完整矩阵见：`authorization_design.md`

## 8. 适用范围

- 需求驱动型测试管理流程
- 早期阶段或单需求单归属的用例管理

## 9. 局限与演进建议

当前局限：

- 不支持“一个用例覆盖多个需求”。

演进建议：

1. 如需多对多关系，引入关联表 `Requirement_Case_Map`。
2. 保留 `ref_req_id` 作为“主需求”字段，兼容历史数据。
3. 增加关系变更审计字段，提升可追溯性。
4. 对删除需求、跨需求迁移等高风险操作补充约束测试。

## 10. 当前代码实现要点

- `Test_Case` 模型包含 `ref_req_id`。
- 创建/更新用例时校验 `ref_req_id` 对应需求存在。
- 支持按 `ref_req_id` 查询测试用例。

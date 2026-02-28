# Backend 文档总览

更新时间：2026-02-28

## 文档边界

- 本目录（`backend/docs`）只保留“后端实现相关”的设计说明：
  - 权限模型与鉴权策略
  - 路由权限矩阵
  - 后端数据约束与关系规则
- 主目录（`docs`）保留“产品级/跨端”文档：
  - 字段定义、登录接入、架构总览、BOM 方案

## 与主目录 docs 的关系

- 字段权威定义：`../../docs/测试需求字段定义.md`、`../../docs/测试用例字段定义.md`
- 测试设计与 BOM 背景：`../../docs/测试设计与BOM关联方案.md`
- 后端统一接口返回规范：`../../docs/后端接口说明.md`

本目录文档不再重复上述内容，只描述后端落地细节。

## 当前文档清单

1. `authorization_design.md`
   - 后端鉴权链路、错误语义、路由权限矩阵（唯一维护入口）
2. `permission_validation_patterns.md`
   - 权限校验模式与分层策略建议
3. `rbac_design.md`
   - RBAC 数据模型、角色能力、接口映射（与当前代码对齐）
4. `requirement_testcase_relation_design.md`
   - 需求与用例的一对多关系约束和查询策略
5. `测试需求测试用例设计方案.md`
   - 后端视角的测试规格设计说明（精简版）

## 本次整理说明

- 已删除重复文档：`rbac_api_permissions.md`
  - 原因：内容与 `authorization_design.md` 的“路由权限矩阵”章节重复。

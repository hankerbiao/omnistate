# Backend 文档总览

更新时间：2026-03-03

## 文档边界

- `docs/backend/` 只保留后端实现相关设计说明：
  - 权限模型与鉴权策略
  - 路由权限矩阵
  - 后端数据约束与关系规则
- `docs/` 保留产品级或跨端文档：
  - 字段定义、登录接入、架构总览、BOM 方案

## 与项目级文档关系

- 字段权威定义：`../测试需求字段定义.md`、`../测试用例字段定义.md`
- 测试设计与 BOM 背景：`../测试设计与BOM关联方案.md`
- 后端统一接口返回规范：`../后端接口说明.md`

本目录文档不重复上述内容，聚焦后端落地细节。

## 当前文档清单

1. `authorization_design.md`
   - 后端鉴权链路、错误语义、路由权限矩阵（唯一维护入口）
2. `permission_validation_patterns.md`
   - 权限校验模式与分层策略建议
3. `rbac_design.md`
   - RBAC 数据模型、角色能力、接口映射（与当前代码对齐）
4. `navigation_page_backend_impl.md`
   - 导航管理后端实现说明
5. `requirement_testcase_relation_design.md`
   - 需求与用例关系约束、接口映射与演进建议

## 整理说明

- 已将原 `backend/docs` 收口到 `docs/backend`。
- 已合并重复文档：
  - `测试需求测试用例设计方案.md` -> `requirement_testcase_relation_design.md`

# 文档总览（docs）

更新时间：2026-03-03

## 1. 文档分层

- `docs/`：项目级与跨端文档（对前后端都生效）
- `docs/backend/`：后端实现细节与权限设计
- `docs/changes/`：阶段性变更记录（合并后的归档）

## 2. 项目级文档

- `项目架构规范.md`：后端分层与工程规范
- `后端接口说明.md`：统一响应与健康检查约定
- `认证与登录指南.md`：登录流程与联调排查
- `测试字段文档总览.md`：字段体系总入口
- `测试需求字段定义.md`：需求字段定义
- `测试用例字段定义.md`：用例字段定义
- `测试设计与BOM关联方案.md`：业务背景与关联价值
- `前后端字段统一说明-登录需求用例.md`：创建请求字段对齐规范
- `自动化测试用例数据结构与关联设计.md`：自动化用例库设计建议

## 3. 后端文档

见 `docs/backend/README.md`，主要包括：

- `authorization_design.md`
- `permission_validation_patterns.md`
- `rbac_design.md`
- `navigation_page_backend_impl.md`
- `requirement_testcase_relation_design.md`

## 4. 变更归档

- `changes/2026-03-02_03_阶段变更汇总.md`：DUT 录入优化、req_id 约束收敛、导航管理实现与修复

## 5. 维护约定

1. 新增文档默认放到 `docs/`，仅后端实现细节放 `docs/backend/`。
2. 同主题文档优先合并，避免并行多份“总结/报告/验证”。
3. 阶段性产出收口到 `docs/changes/`，不再散落根目录。

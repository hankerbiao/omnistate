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

## 4. VitePress API 文档

- `index.md` - 项目首页
- `api/` - VitePress API 接口文档
  - `index.md` - API 概览
  - `auth.md` - 认证说明
  - `workflow.md` - 工作流管理
  - `requirements.md` - 测试需求
  - `test-cases.md` - 测试用例
  - `execution.md` - 测试执行
  - `assets.md` - 资产管理
  - `auth-modules.md` - 认证授权
  - `health.md` - 系统健康

### 启动 VitePress 文档

```bash
# 安装依赖（已在项目根目录执行）
npm install

# 启动开发服务器
npm run docs:dev

# 构建生产版本
npm run docs:build

# 预览构建结果
npm run docs:preview
```

## 5. 变更归档

- `changes/2026-03-02_03_阶段变更汇总.md`：DUT 录入优化、req_id 约束收敛、导航管理实现与修复
- `changes/2026-03-03_vitepress_docs_init.md`：初始化 VitePress 服务并生成完整 API 文档

## 6. 维护约定

1. 新增文档默认放到 `docs/`，仅后端实现细节放 `docs/backend/`。
2. 同主题文档优先合并，避免并行多份”总结/报告/验证”。
3. 阶段性产出收口到 `docs/changes/`，不再散落根目录。
4. API 文档使用 VitePress 管理，通过 `/api/` 路径访问。

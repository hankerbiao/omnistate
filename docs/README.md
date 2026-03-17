# 文档总览（docs）

更新时间：2026-03-17

## 目录原则

- 根目录只保留少量权威文档，避免同主题多份总览并行
- `backend/` 只放后端落地设计
- `api/` 只放 VitePress API 页面
- `changes/` 只放阶段性归档

## 根目录主文档

- `文档治理与重构方案.md`：文档治理规则、目标结构与处置清单
- `项目架构规范.md`：后端分层、依赖方向、工程约束
- `接口与认证说明.md`：统一响应、健康检查、登录接入
- `测试对象与字段规范.md`：需求/用例字段与创建约束
- `测试设计与BOM关联方案.md`：需求、用例、BOM 与自动化关系
- `测试执行集成方案.md`：任务下发、回调协议与 SDK 设计

## 子目录

- `backend/README.md`：后端设计文档入口
- `api/index.md`：API 文档入口
- `changes/2026-03-02_03_阶段变更汇总.md`：阶段变更归档

## VitePress

```bash
npm install
npm run docs:dev
npm run docs:build
npm run docs:preview
```

## 维护约定

1. 同主题只保留一个主文档，其余内容并入章节。
2. 接口细节优先维护在 `api/`，根目录只保留接入级说明。
3. 设计稿沉淀后优先合并，避免继续扩散根目录文件数。
4. `docs/node_modules`、`.vitepress/cache`、`.vitepress/dist` 不作为长期跟踪内容。
5. “当前实现”和“未来方案”必须分开写，避免把规划描述成已上线能力。

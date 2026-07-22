# DML V4 开放平台文档站

本目录是 DML V4 开放平台的 VitePress 文档站，收纳项目概览、设计文档、使用手册、API 参考、配置说明、扩展指南和运维排障内容。

## 本地开发

```bash
npm install
npm run dev
```

默认访问地址：

```text
http://127.0.0.1:8818
```

## 构建与预览

```bash
npm run build
npm run preview
```

构建产物位于：

```text
.vitepress/dist
```

## 目录结构

```text
docs/
├── .vitepress/          # VitePress 配置与主题
├── guide/               # 快速开始、使用手册、本地联调
├── design/              # 总体架构、网关设计、前端设计
├── backend/             # 后端模块说明
├── frontend/            # 前端控制台说明
├── reference/           # API、配置、扩展参考
├── operations/          # 部署、测试、故障排查
├── public/              # 静态资源
└── index.md             # 文档站首页
```

## 内容维护

- 新增页面后，请同步更新 `.vitepress/config.ts` 中的侧边栏。
- 命令、端口、环境变量应以代码中的 `README.md`、`package.json`、`pyproject.toml` 和 `config.py` 为准。
- 开放能力文档应与 `backend/gateway_service/core/catalog.py` 保持一致。

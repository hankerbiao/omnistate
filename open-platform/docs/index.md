---
layout: home

hero:
  name: DML V4 开放平台
  text: API 网关、开放能力目录与开发者控制台
  tagline: 面向外部集成、自动化流水线与 AI 工具调用的统一开放入口。
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/quick-start
    - theme: alt
      text: 架构设计
      link: /design/architecture

features:
  - title: 统一开放 API
    details: 通过 /api/v1/open 暴露稳定契约，内部可代理、聚合或本地处理 DML 主后端能力。
  - title: 网关治理能力
    details: 内置 API Key、Scope 权限、用户配额、调用审计、上游转发、负载均衡和熔断保护。
  - title: 开发者控制台
    details: 前端提供概览、密钥、能力目录、在线调试、调用日志、用户权限和配额管理页面。
  - title: 可扩展工程结构
    details: gateway_service 使用 domain/api/core/infrastructure/common 五层结构，便于扩展能力和替换实现。
---

## 项目定位

`open-platform/` 是 DML V4 的开放平台子项目，统一收纳开放平台前端、后端网关服务、MCP 服务和文档站点。它不直接替代 DML 主后端，而是在主后端之前提供一个面向开放集成场景的治理入口。

当前代码快照的核心后端包括 `backend/gateway_service` 和 `backend/mcp_server`。MCP 服务复用开放平台网关的能力目录、API Key 鉴权、SQLite 仓储、上游转发和调用日志。

## 代码目录

```text
open-platform/
├── backend/
│   ├── gateway_service/       # FastAPI 开放平台网关
│   ├── mcp_server/            # MCP 工具服务
│   ├── tests/                 # 后端单元测试
│   ├── pyproject.toml         # 后端依赖与测试配置
│   └── README.md
├── frontend/
│   ├── src/                   # React 控制台
│   ├── package.json
│   └── README.md
├── docs/                      # 当前 VitePress 文档站
└── README.md
```

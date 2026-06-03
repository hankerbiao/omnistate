# 工作流模块（Workflow Module）

配置驱动的工作流引擎：事项类型、状态、流转规则存 MongoDB，由 JSON 种子初始化。

## 文档（推荐阅读）

VitePress 手册（更完整）：

| 文档 | 路径 |
|------|------|
| 概览 | `backend/docs/modules/workflow/index.md` |
| 架构与设计 | `backend/docs/modules/workflow/architecture.md` |
| 数据模型 | `backend/docs/modules/workflow/data-models.md` |
| 状态与流转 | `backend/docs/modules/workflow/state-and-flow.md` |
| HTTP API | `backend/docs/modules/workflow/api.md` |
| 配置与初始化 | `backend/docs/modules/workflow/configuration.md` |

## 快速命令

```bash
cd backend
python app/init_mongodb.py   # 从 app/configs/*.json 同步配置
python -m app.main            # 启动前会 validate_workflow_consistency
```

## 目录结构

- `api/` — FastAPI 路由（`/api/v1/work-items`）
- `application/` — `WorkflowCommandService`、`MutationService`、`QueryService`
- `domain/` — `rules.py`、`policies.py`、异常
- `repository/models/` — Beanie 文档
- `schemas/` — API 模型
- `docs/workflow.md` — 模块内补充笔记

## 核心模型

- `SysWorkTypeDoc` / `SysWorkflowStateDoc` / `SysWorkflowConfigDoc` — 配置
- `BusWorkItemDoc` — 业务事项（`current_state` 权威来源）
- `BusFlowLogDoc` — 流转审计

## API 前缀

`/api/v1/work-items`（见 `app/shared/api/main.py`）

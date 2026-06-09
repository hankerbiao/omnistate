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

- `api/` — FastAPI 路由（仅 HTTP 映射）
- `application/` — 用例编排层：`WorkflowCommandService`（写侧公共 API）、`WorkflowQueryService`（读侧公共 API）、`WorkflowMutationService`（模块内部实现）
- `domain/` — `rules.py`、`policies.py`、领域异常
- `repository/models/` — Beanie 文档
- `schemas/` — API 输入输出模型
- `service/` — （历史遗留，极少使用）
- `docs/workflow.md` — 模块内补充笔记

## 核心模型

- `SysWorkTypeDoc` / `SysWorkflowStateDoc` / `SysWorkflowConfigDoc` — 配置
- `BusWorkItemDoc` — 业务事项（`current_state` 权威来源）
- `BusFlowLogDoc` — 流转审计

## API 前缀

`/api/v1/work-items`（见 `app/shared/api/main.py`）

# Workflow 模块

`workflow` 是 DML V4 后端的**配置驱动工作流引擎**：管理业务事项（Work Item）的生命周期、状态流转、处理人变更与审计日志。测试需求、测试用例等业务实体通过 `test_specs` 模块创建**投影文档**，并用 `workflow_item_id` 关联到 `BusWorkItemDoc`。

## 文档导航

| 文档 | 内容 |
|------|------|
| [架构与设计](./architecture.md) | 分层、配置驱动模型、事务流转、与 test_specs 集成 |
| [数据模型](./data-models.md) | MongoDB 集合、索引、序列化与父子关系 |
| [状态与流转](./state-and-flow.md) | 状态机规则、处理人策略、权限 properties |
| [HTTP API](./api.md) | 路由、权限、请求/响应约定 |
| [配置与初始化](./configuration.md) | JSON 配置、`init_mongodb`、启动校验、扩展新类型 |

代码内说明见 [`app/modules/workflow/README.md`](../../../app/modules/workflow/README.md)。  
更细的模块内笔记见 [`app/modules/workflow/docs/workflow.md`](../../../app/modules/workflow/docs/workflow.md)。

## 模块职责（一句话）

**当前状态 + 动作** 查 MongoDB 流转表 → 校验权限与必填字段 → 更新 `BusWorkItemDoc` 并写 `BusFlowLogDoc`；规则全部来自 `app/configs/*.json`，改流程通常无需改 Python。

## 核心目录

```
app/modules/workflow/
├── api/
│   ├── routes.py              # 聚合 /work-items 子路由
│   ├── routes_catalog.py      # 类型 / 状态 / 配置目录
│   ├── routes_items.py        # 创建、列表、搜索、详情
│   ├── routes_transitions.py  # 流转、改派、删除、日志、可用动作
│   ├── routes_relations.py    # 需求 ↔ 测试用例层级查询
│   └── dependencies.py        # DI：Query / Mutation / Command
├── application/
│   ├── workflow_command_service.py  # 用例编排 + MutationHook
│   ├── mutation_service.py          # 写侧：创建 / 流转 / 删除 / 改派
│   ├── query_service.py             # 读侧：列表 / 搜索 / 可用流转
│   ├── commands.py                  # Command DTO
│   ├── common.py                    # 查询基类、序列化、事务辅助
│   └── ports.py                     # Gateway / Hook 协议
├── domain/
│   ├── rules.py                     # 必填字段、处理人策略（纯函数）
│   ├── policies.py                  # 流转 / 删除 / 改派权限
│   └── exceptions.py                # 领域异常
├── repository/models/
│   ├── system.py                    # SysWorkType / State / Config
│   └── business.py                  # BusWorkItem / BusFlowLog
└── schemas/                         # API 请求与响应模型
```

## 关键调用链

| 场景 | 调用链 |
|------|--------|
| 创建事项 | API → `WorkflowCommandService.create_work_item` → `WorkflowMutationService.create_item` |
| 状态流转 | API → `WorkflowCommandService.transition_work_item` → `handle_transition`（Mongo 事务） |
| 可用动作 | API → `WorkflowQueryService.get_item_with_transitions`（按当前用户过滤权限） |
| 删除 | API → `delete_work_item` → Hook `before_delete` / `after_delete` → 软删除 |
| test_specs 创建需求/用例 | `TestCaseService` / 事务 → `WorkflowItemGateway` + 投影文档 |

## 与其它模块的关系

| 模块 | 关系 |
|------|------|
| **test_specs** | 通过 `WorkflowCommandService`（带 `TestSpecsWorkflowProjectionHook`）创建/删除；列表展示用 `workflow_item_id` 投影 `current_state` |
| **auth** | API 使用 `work_items:read` / `work_items:write` / `work_items:transition`；流转权限另见 `domain/policies.py` |
| **execution** | 无直接依赖；测试执行编排独立 |
| **workflow → test_specs** | **禁止**反向依赖业务文档 |

## 常见修改场景

| 需求 | 优先位置 |
|------|----------|
| 新增事项类型或改流转图 | `app/configs/<type>.json` → `python app/init_mongodb.py` |
| 改流转必填 / 处理人策略 | JSON `required_fields`、`target_owner_strategy` |
| 改谁能点某个按钮 | JSON `properties`（见 [状态与流转](./state-and-flow.md)） |
| 改删除联动 | `test_specs/.../workflow_projection_hook.py` |
| 改列表筛选语义 | `application/common.py` 的 `base_item_query` |
| 改 API 字段 | `schemas/` + `routes_*.py` |

## 风险点

- **配置不一致**：`init_mongodb.py` 种子前校验 + 启动时 `validate_workflow_consistency()`；脏配置会导致服务无法启动（空库仅告警）。
- **事务依赖**：流转与删除要求 MongoDB **副本集 + 事务**；单机无事务时会 `RuntimeError` 拒绝非原子操作。
- **双写一致性**：`bus_work_items` 与 `test_requirements` / `test_cases` 由事务或 Hook 维护；只改一侧会导致列表状态与详情不一致。
- **标题唯一**：同 `type_code` 下未删除事项的 `title` 唯一（部分索引），创建重复标题会 400。

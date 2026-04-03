# Workflow 模块

## 模块职责

`workflow` 是后端的业务流转基础设施，负责：

- 事项类型、状态、流转配置
- 业务事项创建与查询
- 状态流转、改派、删除
- 流转日志审计

## 核心目录

- `api/`
  HTTP 路由与依赖注入
- `application/query_service.py`
  读侧查询
- `application/mutation_service.py`
  写侧流转与删除
- `application/workflow_command_service.py`
  用例级命令编排
- `domain/`
  策略、规则、异常
- `repository/models/`
  Beanie 文档模型

## 关键模型

- `SysWorkTypeDoc`
- `SysWorkflowStateDoc`
- `SysWorkflowConfigDoc`
- `BusWorkItemDoc`
- `BusFlowLogDoc`

## 关键字段说明

### `SysWorkflowConfigDoc`

- `type_code`
  事项类型编码，例如需求、测试用例等
- `from_state`
  当前允许流转的源状态
- `action`
  当前可执行动作
- `to_state`
  动作执行后的目标状态
- `target_owner_strategy`
  流转后处理人如何计算
- `required_fields`
  当前动作要求前端或调用方提供的业务字段

### `BusWorkItemDoc`

- `type_code`
  事项所属业务类型
- `title`
  事项标题
- `creator_id`
  创建人
- `current_state`
  当前状态，是 workflow 的真实状态来源
- `current_owner_id`
  当前处理人
- `parent_item_id`
  父事项 ID，用于表达需求与用例等层级关系
- `is_deleted`
  逻辑删除标记

### `BusFlowLogDoc`

- `work_item_id`
  对应事项 ID
- `from_state`
  变更前状态
- `to_state`
  变更后状态
- `action`
  本次执行的动作
- `operator_id`
  操作人
- `payload`
  本次流转携带的表单或审计数据

## 关键调用链

- 创建事项：
  API -> `WorkflowCommandService.create_work_item()` -> `WorkflowMutationService.create_item()`
- 状态流转：
  API -> `WorkflowCommandService.transition_work_item()` -> `WorkflowMutationService.handle_transition()`
- 查询事项：
  API -> `WorkflowQueryService`

## 关键业务规则

- 流转规则由 Mongo 中的 workflow 配置驱动
- 必填字段校验在流转时执行
- 处理人策略由 domain rules 计算
- 删除和改派都会写流转日志

## 与其他模块的关系

- `test_specs` 通过 gateway 方式创建和读取 workflow 事项
- `workflow` 不应该反向依赖 `test_specs` 业务文档

## 常见修改场景

- 改流转配置：优先看 `app/configs/*.json`
- 改流转行为：看 `mutation_service.py` 和 `domain/rules.py`
- 改返回字段：看 `query_service.py` 和 `schemas/`

## 风险点

- 配置不一致会在启动阶段阻断服务
- 若业务文档和 workflow 事项脱节，状态投影会异常

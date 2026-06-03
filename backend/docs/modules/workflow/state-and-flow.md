# Workflow 状态与流转

## 状态机模型

状态机由 **有向边** 组成，每条边对应 `SysWorkflowConfigDoc` 一行：

```text
[type_code]  from_state --action--> to_state
```

- **节点**：`sys_workflow_states.code`
- **边**：`(type_code, from_state, action)` 唯一
- **当前指针**：`BusWorkItemDoc.current_state`

前端通过 `GET /work-items/{id}/transitions` 获取当前状态下、当前用户可执行的边列表。

## 内置事项类型（当前仓库）

### REQUIREMENT（需求）

配置：`app/configs/requirement.json`

典型路径（简化）：

```text
DRAFT --SUBMIT--> PENDING_REVIEW
PENDING_REVIEW --APPROVE--> PENDING_DEVELOP
PENDING_REVIEW --REJECT--> DRAFT
PENDING_DEVELOP --START--> DEVELOPING
DEVELOPING --FINISH--> PENDING_TEST
PENDING_TEST --PASS--> PENDING_UAT
PENDING_TEST --REJECT--> DEVELOPING
PENDING_UAT --PASS--> PENDING_RELEASE
PENDING_UAT --REJECT--> DEVELOPING
PENDING_RELEASE --PUBLISH--> RELEASED
```

`RELEASED` 在 `global_config.json` 中标记 `is_end: true`。

### TEST_CASE（测试用例）

配置：`app/configs/test_case.json`

```text
DRAFT --ASSIGN--> ASSIGNED
ASSIGNED --START_WRITE--> DEVELOPING
DEVELOPING --SUBMIT_REVIEW--> PENDING_REVIEW
PENDING_REVIEW --APPROVE--> DONE
PENDING_REVIEW --REJECT--> DEVELOPING
```

`DONE` 为终态。

## 处理人策略（target_owner_strategy）

实现：`domain/rules.resolve_owner`

| 策略 | 行为 |
|------|------|
| **KEEP** | `current_owner_id` 不变 |
| **TO_CREATOR** | 设为 `creator_id`（驳回给创建者等场景） |
| **TO_SPECIFIC_USER** | 使用 `form_data.target_owner_id`；缺失则 `MissingRequiredFieldError` |

流转后写入 `BusWorkItemDoc.current_owner_id`，并出现在流转响应的 `new_owner_id`。

## 必填字段（required_fields）

`ensure_required_fields` 要求 `form_data` **包含键**（值可为空字符串，但键必须存在）。

`build_process_payload` 写入日志的内容：

- 所有 `required_fields` 对应值
- 若 `form_data` 含 `remark` 且非 `null`，一并写入 `payload`

常见字段：

| 字段 | 典型用途 |
|------|----------|
| `target_owner_id` | 指定下一处理人（配合 `TO_SPECIFIC_USER`） |
| `priority` | 需求优先级 |
| `comment` | 审批意见 |

API 请求体：`POST /work-items/{id}/transition` 的 `form_data` 对象。

## 权限（properties）

实现：`domain/policies.can_transition`

判断顺序（摘要）：

1. `properties.owner_only` → 仅当前负责人（`current_owner_id`）
2. `properties.creator_only` → 仅创建人
3. `properties.allowed_actor_types` → 匹配 `admin` / `creator` / `current_owner` / `reviewer` / `system` 等
4. 若配置了 `allowed_role_ids` → 角色集合交集（兼容 `ROLE_QA` 与 `QA`）
5. 若都未配置 → **默认** 仅创建人或当前负责人

**ADMIN 不在流转层无条件放行**；管理员仍可改派（`can_reassign`）或删除（`can_delete_work_item`）。

需求配置示例（待审核）：

```json
"properties": {"owner_only": true}
```

表示只有当前负责人（提交时指派的审核人）可以执行该动作。

提交示例：

```json
"properties": {"creator_only": true}
```

表示只有创建人可以提交草稿。

### 其它操作权限

| 操作 | 规则 |
|------|------|
| **改派** `can_reassign` | ADMIN 或当前负责人 |
| **删除** `can_delete_work_item` | ADMIN 或创建人 |

改派、删除权限**不**读取 `SysWorkflowConfigDoc.properties`，与具体 transition 无关。

## 特殊动作（非配置表）

| action | 触发方式 | 状态变化 |
|--------|----------|----------|
| `DELETE` | `DELETE /work-items/{id}` | 软删除；日志 `from_state=to_state=当前` |
| `REASSIGN` | `POST .../reassign` | 状态不变，仅改 `current_owner_id` |

## 流转 API 与异常

| 异常 | HTTP | 含义 |
|------|------|------|
| `WorkItemNotFoundError` | 404 | 事项不存在或已删除 |
| `InvalidTransitionError` | 400 | 当前状态不支持该 action |
| `MissingRequiredFieldError` | 400 | 缺必填字段 |
| `PermissionDeniedError` | 403 | 无权执行 |
| `RuntimeError`（事务） | 500 | Mongo 未初始化或不支持事务 |

## 查询「我能做什么」

`GET /work-items/{id}/transitions` 返回：

```json
{
  "item_id": "...",
  "current_state": "PENDING_REVIEW",
  "available_transitions": [
    {
      "action": "APPROVE",
      "to_state": "PENDING_DEVELOP",
      "target_owner_strategy": "TO_SPECIFIC_USER",
      "required_fields": ["target_owner_id", "comment"]
    }
  ],
  "creator": "...",
  "current_owner": "..."
}
```

列表已按当前用户角色过滤；仍须在 `POST .../transition` 时服务端二次校验。

## 终态（is_end）

`SysWorkflowStateDoc.is_end` 用于标识状态是否「结束」：

- 种子时：若 JSON 未显式 `is_end`，则 **没有任何出边** 的状态推导为终态
- 也可在 `global_config.json` 中显式设置，如 `RELEASED`、`DONE`

终态事项仍可被软删除；是否允许从终态再流转取决于是否配置了出边（当前需求/用例配置通常不再流出）。

## 相关文档

- [配置与初始化](./configuration.md) — 如何改 JSON 增删边
- [HTTP API](./api.md) — 接口参数
- [架构与设计](./architecture.md) — 事务与 Hook

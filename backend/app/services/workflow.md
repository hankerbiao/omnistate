# 任务流转说明（AsyncWorkflowService）

本文档只关注「任务/事项流转」相关的核心设计与实现，方便前后端在对接和扩展流程时统一理解。

相关核心代码：

- 工作流服务：[workflow_service.py](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow_service.py)
- 业务路由：[work_items.py](file:///Users/libiao/Desktop/github/test/backend/app/api/routes/work_items.py)
- 文档模型：
  - 系统配置模型：[system.py](file:///Users/libiao/Desktop/github/test/backend/app/models/system.py)
  - 业务模型：[business.py](file:///Users/libiao/Desktop/github/test/backend/app/models/business.py)

---

## 1. 核心概念

### 1.1 业务事项（BusWorkItemDoc）

业务事项是整个任务流转的核心实体，对应：

- 模型：`BusWorkItemDoc`（业务文档）
- 关键字段：
  - `type_code`：事项类型（如 `REQUIREMENT`、`TEST_CASE`）
  - `current_state`：当前状态（对应 `WorkItemState` 枚举）
  - `current_owner_id`：当前处理人
  - `creator_id`：创建人
  - `is_deleted`：逻辑删除标记

所有与流转相关的读写，都围绕这一实体展开。

### 1.2 流转配置（SysWorkflowConfigDoc）

流转规则由配置驱动，对应：

- 模型：`SysWorkflowConfigDoc`
- 核心字段：
  - `type_code`：事项类型
  - `from_state`：当前状态
  - `action`：动作（如 `SUBMIT`、`APPROVE`、`REJECT`）
  - `to_state`：流转后的目标状态
  - `target_owner_strategy`：处理人策略（见 1.4）
  - `required_fields`：执行此动作时必填的业务字段

每一条配置代表「某类型事项在某状态下执行某动作时该如何流转」。

### 1.3 流转日志（BusFlowLogDoc）

每一次状态变更或处理人变更，都会记录一条流转日志，对应：

- 模型：`BusFlowLogDoc`
- 关键字段：
  - `work_item_id`：对应的业务事项 ID
  - `from_state`：原状态
  - `to_state`：目标状态
  - `action`：执行的动作（包括业务动作、`REASSIGN`、`DELETE` 等）
  - `operator_id`：操作人
  - `payload`：本次操作携带的业务数据（如审批意见、改派目标等）

### 1.4 处理人策略（OwnerStrategy）

流转配置中的 `target_owner_strategy` 控制「流转后任务的处理人」：

- `KEEP`：保持当前处理人不变
- `TO_CREATOR`：流转回创建人
- `TO_SPECIFIC_USER`：流转到表单中指定的用户（需要 `target_owner_id` 字段）

实际计算逻辑由 `AsyncWorkflowService._apply_owner_strategy` 负责。

---

## 2. 状态流转核心流程（handle_transition）

核心接口：

- 服务方法：`AsyncWorkflowService.handle_transition`
- 典型调用路径：
  - HTTP 路由：[work_items.py](file:///Users/libiao/Desktop/github/test/backend/app/api/routes/work_items.py)
    中的 `POST /api/v1/work-items/{item_id}/transition`

### 2.1 入参

`handle_transition` 的关键入参：

- `work_item_id: str`：要流转的事项 ID
- `action: str`：当前要执行的动作
- `operator_id: int`：操作人 ID
- `form_data: Dict[str, Any]`：业务表单数据（用于校验必填字段和计算处理人）

### 2.2 流程步骤

状态流转的完整流程如下（对应 `handle_transition` 内部实现）：

1. **校验事项存在性**
   - 根据 `work_item_id` 读取 `BusWorkItemDoc`
   - 若不存在或已逻辑删除（`is_deleted = True`），抛出 `WorkItemNotFoundError`

2. **匹配流转配置**
   - 根据：
     - `item_doc.type_code`
     - `item_doc.current_state`
     - `action`
   - 在 `SysWorkflowConfigDoc` 中查找唯一匹配的配置
   - 若找不到，抛出 `InvalidTransitionError`，表示当前状态下不允许执行该动作

3. **校验必填业务字段**
   - 读取配置中的 `required_fields`
   - 检查这些字段是否全部存在于 `form_data` 中
   - 若缺失，抛出 `MissingRequiredFieldError`
   - 同时构造本次操作的 `process_payload`，写入日志使用

4. **计算新状态与处理人**
   - `old_state = item_doc.current_state`
   - `new_state = config_doc.to_state`
   - 调用 `_apply_owner_strategy` 根据策略计算 `new_owner_id`：
     - `TO_CREATOR`：使用 `creator_id`
     - `TO_SPECIFIC_USER`：从 `form_data["target_owner_id"]` 读取
     - 其他情况：保持 `current_owner_id` 不变

5. **更新事项**
   - 更新 `item_doc.current_state = new_state`
   - 更新 `item_doc.current_owner_id = new_owner_id`
   - 调用 `item_doc.save()` 持久化到数据库

6. **写入流转日志**
   - 创建 `BusFlowLogDoc`，字段包括：
     - `work_item_id`
     - `from_state`
     - `to_state`
     - `action`
     - `operator_id`
     - `payload`（即 `process_payload`）
   - 调用 `log_entry.insert()` 写入日志集合

7. **返回结果**
   - 将最新的 `item_doc` 转为字典并附带字符串化的 `id`
   - 返回结构包含：
     - `work_item_id`
     - `from_state`
     - `to_state`
     - `action`
     - `new_owner_id`
     - `work_item`（更新后的事项详情）

---

## 3. 处理人策略逻辑（_apply_owner_strategy）

实现位置：

- [workflow_service.py](file:///Users/libiao/Desktop/github/test/backend/app/services/workflow_service.py)
  中的 `AsyncWorkflowService._apply_owner_strategy`

输入参数：

- `work_item: Dict[str, Any]`：当前事项信息（字典形式）
- `config: Dict[str, Any]`：当前匹配到的流转配置
- `form_data: Dict[str, Any]`：本次操作的表单数据

核心逻辑：

- 读取 `config["target_owner_strategy"]`，默认 `KEEP`
- 分支处理：
  - `TO_CREATOR`：返回 `work_item["creator_id"]`
  - `TO_SPECIFIC_USER`：
    - 从 `form_data` 中读取 `target_owner_id`
    - 若不存在则抛出 `MissingRequiredFieldError("target_owner_id")`
  - 其他（含 `KEEP`）：返回 `work_item["current_owner_id"]`

这一策略保证了「状态如何跳转」和「任务归谁处理」都可以通过配置文件控制，而无需改动代码。

---

## 4. 与任务流转直接相关的 HTTP 接口

所有接口前缀：`/api/v1/work-items`

路由实现见：

- [work_items.py](file:///Users/libiao/Desktop/github/test/backend/app/api/routes/work_items.py)

### 4.1 创建事项（设置初始状态）

- 方法：`POST /api/v1/work-items`
- 对应服务方法：`AsyncWorkflowService.create_item`
- 关键行为：
  - 创建 `BusWorkItemDoc`
  - 初始状态设置为 `WorkItemState.DRAFT`
  - `current_owner_id` 默认设置为 `creator_id`

虽然严格意义上这是「创建」而不是「流转」，但它定义了任务流转的起点（初始状态）。

### 4.2 执行状态流转

- 方法：`POST /api/v1/work-items/{item_id}/transition`
- 对应服务方法：`handle_transition`
- 功能：
  - 按第 2 节所述流程执行状态切换
  - 校验配置和必填字段
  - 应用处理人策略
  - 记录流转日志

### 4.3 改派处理人

- 方法：`POST /api/v1/work-items/{item_id}/reassign`
- 对应服务方法：`reassign_item`
- 特点：
  - 只修改 `current_owner_id`
  - 不改变 `current_state`
  - 写入一条 `action="REASSIGN"` 的流转日志，记录改派信息（以及可选的 `remark`）

在看板等场景下，这属于「任务分配」层面的流转。

### 4.4 流转日志查询

- 方法：`GET /api/v1/work-items/{item_id}/logs`
  - 对应服务方法：`get_logs`
  - 返回单个事项的流转历史，按时间倒序

- 方法：`GET /api/v1/work-items/logs/batch?item_ids=id1,id2,...`
  - 对应服务方法：`batch_get_logs`
  - 批量返回多个事项的流转历史列表
  - 常用于看板：一次性拉取多个任务的状态时间线

这两类接口都是围绕「任务流转历史」展开的。

### 4.5 获取可用下一步动作

- 方法：`GET /api/v1/work-items/{item_id}/transitions`
- 对应服务方法：`get_item_with_transitions`
- 返回结构：
  - `item`：当前事项详情
  - `available_transitions`：当前状态下所有可执行的动作列表，每项内容包括：
    - `action`
    - `to_state`
    - `target_owner_strategy`
    - `required_fields`

前端可以基于这个接口动态渲染「操作按钮」和「表单必填项」。

---

## 5. 配置驱动的流转规则示例

流转规则配置位于：

- 目录：[app/configs](file:///Users/libiao/Desktop/github/test/backend/app/configs)

典型 `workflow_configs` 字段示例（简化）：

```json
{
  "type_code": "REQUIREMENT",
  "from_state": "DRAFT",
  "action": "SUBMIT",
  "to_state": "PENDING_REVIEW",
  "target_owner_strategy": "TO_SPECIFIC_USER",
  "required_fields": ["title", "content", "target_owner_id"]
}
```

含义：

- 当一个 `REQUIREMENT` 类型的事项处于 `DRAFT` 状态时：
  - 执行 `SUBMIT` 动作
  - 若请求体中包含 `required_fields` 中的所有字段：
    - 状态会流转到 `PENDING_REVIEW`
    - 新处理人会根据 `target_owner_id` 决定

`AsyncWorkflowService.handle_transition` 会使用这些配置完成实际的状态和处理人变更，同时写入流转日志。

---

通过以上约定，本项目实现了「**配置驱动的任务流转**」：

- 代码（`AsyncWorkflowService`）只实现通用的流转引擎
- 具体有哪些状态、动作、谁处理、必填什么字段，全部由配置决定
- 修改或新增流程时，只需要调整配置，无需改动核心代码


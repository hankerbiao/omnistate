# 数据库设计评审报告

**评审日期**: 2026-05-09
**评审范围**: 20 个 MongoDB 集合，6 个业务领域

---

## P0 — 必须修复

### 1. DutDoc 明文存储 BMC/OS 密码

`dut.py:26,31` — `bmc_password` 和 `os_password` 以明文 `str` 存入 MongoDB。任何人能访问数据库即可获取所有测试机 BMC/OS 凭据。

**建议**: 写入前用应用层密钥 AES 加密，读取时解密。密钥从环境变量或 Vault 注入，不落库。

### 2. DutDoc 缺少 `@before_event` hook

`dut.py` — 有 `created_at`/`updated_at` 字段但无 `@before_event([Save, Insert])` hook。每次 `doc.save()` 后 `updated_at` 不会自动刷新，依赖业务代码手动设置。已有 `sync_from_tmms` 等多处调用未手动更新。

**建议**: 补上 hook，与其他 18 个模型一致。

### 3. AttachmentDoc 无 `created_at`/`updated_at`

`attachment.py` — 完全没有审计时间戳字段。文件上传、删除时间无法追溯。

**建议**: 至少补 `created_at`。`uploaded_at` 是业务时间（用户上传时刻），`created_at` 是记录写入时间，两者不应混淆。

---

## P1 — 建议修复

### 4. ID 引用体系分裂：PydanticObjectId vs str

workflow 模块的 `BusWorkItemDoc.parent_item_id` 和 `BusFlowLogDoc.work_item_id` 使用 MongoDB `ObjectId`，其余所有集合的引用全部使用业务 `str` ID（如 `task_id`、`case_id`）。

| 模块 | 引用类型 | 示例 |
|------|---------|------|
| workflow | `PydanticObjectId` | `parent_item_id`, `work_item_id` |
| 其他全部 | `str` | `task_id`, `case_id`, `agent_id`, `user_id`, `req_id` |

**问题**: 
- 同一项目两种 ID 体系，增加认知负担和维护成本
- `ObjectId` 不可读，调试和日志中无法直接识别业务含义
- 跨模块引用时无法统一处理

**建议**: 统一为业务 `str` ID（如 `BW-2026-000001`）。workflow 模块单独评估迁移成本。

### 5. sys_counters 无 Beanie 模型，裸用 PyMongo

`sequence_id.py` — `sys_counters` 集合用 `find_one_and_update` + `$inc` 原子生成序列号。没有 Document 模型、没有索引定义、没有字段校验。

**建议**: 至少定义 `SysCounterDoc` 并显式声明索引。当前裸用 PyMongo 绕过了 Beanie 的模型校验和迁移体系。

### 6. BusWorkItemDoc 部分唯一索引依赖 `is_deleted: False`

`business.py` — `(type_code, title)` 的唯一性通过 `partialFilterExpression: {"is_deleted": False}` 实现。这意味着已删除记录的同名约束被打破，一旦物理清除可能破坏唯一性假设。

**建议**: 保持当前设计，但明确文档说明"已删除记录允许同名"的语义。在物理清理脚本中增加冲突检查。

---

## P2 — 规范不一致

### 7. 主键字段命名不统一

| 模式 | 集合 | 
|------|------|
| `xxx_id` | duts, users, roles, permissions(perm_id), test_requirements(req_id), test_cases(case_id), execution_tasks(task_id), execution_agents(agent_id), attachments(file_id) |
| `code` | sys_work_types, sys_workflow_states |
| `view` | navigation_pages |
| `execution_id` | automation_config_instances |
| `event_id` | execution_events |
| `auto_case_id` | automation_test_cases |
| `parameter_set_id` | test_case_parameters |

**问题**: `perm_id` 而非 `permission_id`，`req_id` 而非 `requirement_id`，`code` 和 `view` 不走 `*_id` 模式。

**建议**: 
- `perm_id` → `permission_id`
- `req_id` → `requirement_id`  
- `code` (SysWorkTypeDoc/SysWorkflowStateDoc) 保持，有特定语义
- `view` 保持，有特定语义

### 8. Soft Delete 覆盖不全

| 有 is_deleted | 无 is_deleted | 原因分析 |
|--------------|--------------|---------|
| bus_work_items, attachments, navigation_pages, execution_tasks, execution_agents, test_cases, test_requirements, automation_test_cases, test_case_parameters, automation_config_instances | users, roles, permissions, duts, execution_events, execution_task_cases, bus_flow_logs, sys_work_types, sys_workflow_states, sys_workflow_configs | — |

有 `is_deleted` 的 11 个集合中，部分查询已遗漏 `is_deleted: False` 过滤（如之前修复的 `event_ingest_service` 和 `task_dispatch_coordinator`）。

**无 is_deleted 的合理性分析**:

| 无 is_deleted 的集合 | 是否合理 |
|---------------------|---------|
| users, roles, permissions | **可能不需要** — RBAC 实体通常直接物理删除 |
| execution_events | **合理** — 事件归档，只追加不删除 |
| execution_task_cases | **存疑** — 任务被逻辑删除后，关联 case 也应级联标记 |
| bus_flow_logs | **合理** — 审计日志只追加 |
| sys_work_types/states/configs | **存疑** — 系统配置应支持逻辑删除再恢复 |
| duts | **不合理** — 已有 `source` 和 `source_id` 同步逻辑，删除应该是逻辑删除 |
| sys_counters | **合理** — 序列号计数器 |

**建议**: 
- `duts` 加 `is_deleted` 并改为软删除（当前 `delete_dut` 是物理删除）
- `execution_task_cases` 加 `is_deleted`，任务软删除时级联标记
- `sys_work_*` 评估是否需要软删除

### 9. AttachmentDoc 字段别名冗余

`attachment.py` — 所有字段使用 `Field(alias="field_name")`，别名与 Python 属性名完全相同。`alias` 的作用是序列化/反序列化时做名称映射，同名字段不需要。

**建议**: 删除所有与属性名一致的 `alias`，仅保留真正做名称映射的场景。

### 10. 缺少 `is_active` 一致性

仅 `NavigationPageDoc` 和 `TestCaseDoc` 有 `is_active` 字段用于启用/禁用。其余集合（users 用 `status`、automation_test_cases 用 `status`）各自定义不同方式表达激活状态。

**建议**: 保持现状（不同领域语义不同），但文档说明各集合的"激活"表达方式。

---

## 索引评审

### 11. 复合索引字段顺序

`execution_tasks` 的 18 个索引中有多个复合索引格式为 `(field, created_at DESC)`，这是正确的查询模式（等值 + 排序）。

但 `execution_task_cases` 缺少 `(task_id, dispatch_status)` 复合索引——case 下发状态查询很常见。

### 12. 缺失索引

| 集合 | 缺失索引 | 查询场景 |
|------|---------|---------|
| `execution_task_cases` | `(task_id, dispatch_status)` | 查询某任务下发失败的 case |
| `attachments` | 无任何索引 | `file_id` 应有唯一索引，`uploaded_by` 应有普通索引 |
| `bus_flow_logs` | `operator_id` | 按操作人查询审计日志 |

### 13. 冗余索引

`execution_tasks` 的 `dedup_key` 同时有单字段索引和 `(dedup_key, consume_status)` 复合索引。MongoDB 可以只用复合索引的前缀完成等值查询，单字段索引冗余。

---

## 安全性补充

### 14. UserDoc password_salt 与 password_hash 同文档存储

`rbac.py` — `password_salt` 和 `password_hash` 同存一个文档。这是标准做法（验证需要 salt），不是安全问题。但文档注释应说明算法（如 `pbkdf2_sha256` 或 `bcrypt`）。

---

## 汇总

| 严重度 | 数量 | 关键条目 |
|--------|------|---------|
| P0 | 3 | DutDoc 明文密码、缺少 before_event hook、AttachmentDoc 无时间戳 |
| P1 | 3 | ID 体系分裂、sys_counters 裸 PyMongo、部分唯一索引 |
| P2 | 6 | 主键命名、soft delete 覆盖、别名冗余、is_active 不一致、缺失/冗余索引 |

**建议修复优先级**:
1. DutDoc 密码加密（P0，安全）
2. AttachmentDoc 补时间戳 + 索引（P0 + P2）
3. DutDoc 补 hook（P0）
4. sys_counters 建模（P1）
5. ID 体系统一评估（P1）
6. P2 项逐步收敛

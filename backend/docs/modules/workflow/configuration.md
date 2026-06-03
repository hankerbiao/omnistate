# Workflow 配置与初始化

## 配置文件布局

```
backend/app/configs/
├── global_config.json   # 全局 states 定义
├── requirement.json     # REQUIREMENT 类型 + 流转边
└── test_case.json       # TEST_CASE 类型 + 流转边
```

`init_mongodb.py` 会扫描 `configs/` 下所有 `.json`，**合并**：

- `work_types` → `sys_work_types`
- `states`（来自各文件，通常只在 global）→ `sys_workflow_states`
- `workflow_configs` → `sys_workflow_configs`

## JSON 结构

### 全局状态（`global_config.json`）

```json
{
  "states": [
    {"code": "DRAFT", "name": "草稿", "is_end": false},
    {"code": "RELEASED", "name": "已上线", "is_end": true}
  ]
}
```

- `is_end` 可省略：种子脚本对「无任何出边」的状态推导为终态

### 业务类型文件（如 `requirement.json`）

```json
{
  "work_types": [["REQUIREMENT", "需求"]],
  "workflow_configs": {
    "REQUIREMENT": [
      {
        "from_state": "DRAFT",
        "action": "SUBMIT",
        "to_state": "PENDING_REVIEW",
        "target_owner_strategy": "TO_SPECIFIC_USER",
        "required_fields": ["target_owner_id", "priority"],
        "properties": {"allowed_role_ids": ["TPM"]}
      }
    ]
  }
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `from_state` / `to_state` | 是 | 须存在于 global `states` |
| `action` | 是 | 同 `(type_code, from_state)` 不可重复 |
| `target_owner_strategy` | 否 | 默认 `KEEP` |
| `required_fields` | 否 | 默认 `[]` |
| `properties` | 否 | 权限扩展，默认 `{}` |

## 初始化命令

```bash
cd backend
python app/init_mongodb.py
```

脚本会：

1. 解析并合并所有 JSON
2. **`_validate_workflow_configs`**：未定义 type/state、重复边等 → 抛错退出
3. Upsert 写入 `sys_work_types`、`sys_workflow_states`、`sys_workflow_configs`

修改 JSON 后需**重新执行**种子脚本，运行中服务不会自动热加载配置。

## 启动时校验

`app/shared/infrastructure/bootstrap.py` → `validate_workflow_consistency()`：

| 条件 | 行为 |
|------|------|
| 三表均为空 | **Warning**，提示运行 `init_mongodb.py` |
| 有配置但无 work_types / states | **RuntimeError**，阻止启动 |
| config 引用未知 `type_code` / `from_state` / `to_state` | **RuntimeError** |

主服务与 Kafka Worker 启动时都会调用（见 `app/main.py`、`kafka_worker_main.py`）。

## 新增一种事项类型（检查清单）

1. 在 `app/configs/` 新建 `my_type.json`：
   - `work_types`: `[["MY_TYPE", "显示名"]]`
   - `workflow_configs.MY_TYPE`: 完整边列表
2. 确认所有 `from_state` / `to_state` 已在 `global_config.json` 的 `states` 中（或在新文件补充 `states`）
3. `python app/init_mongodb.py`
4. 重启后端，确认启动无 consistency 错误
5. 若业务模块需要投影（类似 test_specs）：
   - 实现 `WorkflowItemGateway` / 事务创建
   - 按需实现 `WorkflowMutationHook`
   - **不要**在 workflow 模块 import 业务 Document

## 修改已有流转

| 变更 | 操作 |
|------|------|
| 增删状态 | 改 `global_config.json` + 业务 JSON 边 → 种子 |
| 改按钮权限 | 改对应边的 `properties` → 种子 |
| 改必填项 | 改 `required_fields` → 种子；前端同步 `form_data` |
| 改处理人规则 | 改 `target_owner_strategy` → 种子 |

**注意**：已存在事项的 `current_state` 不会随配置删除而自动迁移；删边可能导致某些状态「无可用动作」，需数据修复或保留兼容边。

## 环境变量

Workflow **不**使用独立 `.env` 键；依赖：

- `MONGO_URI` / `MONGO_DB_NAME`（见 `config.yaml`）
- 事务能力：MongoDB 须为 **Replica Set**（流转/删除）

## 调试配置问题

| 现象 | 排查 |
|------|------|
| 启动报 consistency failed | 对照报错中的 unknown `type_code` / `state`，检查 JSON 与 DB 是否一致 |
| `init_mongodb` 报重复流转 | 同一 `(type, from, action)` 出现两次 |
| 前端无按钮 | `GET .../transitions` 看是否被 `can_transition` 过滤；查 `properties.allowed_role_ids` |
| 流转 400 缺字段 | 对照该 action 的 `required_fields` |

## 相关文档

- [状态与流转](./state-and-flow.md) — 策略与权限语义
- [数据模型](./data-models.md) — 表结构

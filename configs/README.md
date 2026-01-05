# 配置说明文档 (Configs README)

本文档详细说明了 `configs/` 目录下配置文件的结构、字段含义以及如何新增配置。

## 1. 配置文件概览

### `workflow_initial_data.json`
这是系统的核心配置文件，定义了所有的业务类型、状态以及工作流迁移规则。系统启动或初始化时会读取此文件并持久化到数据库。

---

## 2. 字段详细说明

### 2.1 `work_types` (业务类型)
定义系统支持的业务对象类型。
- **格式**: `[ ["CODE", "NAME"], ... ]`
- **示例**: `["REQUIREMENT", "需求"]`
- **说明**: `CODE` 用于程序逻辑识别，`NAME` 用于前端展示。

### 2.2 `states` (状态定义)
定义工作流中可能出现的所有状态。
- **格式**: `[ ["STATE_CODE", "STATE_NAME"], ... ]`
- **示例**: `["DRAFT", "草稿"]`
- **说明**: 状态是全局共享的，不同业务流程可以复用相同的状态代码。

### 2.3 `workflow_configs` (工作流迁移规则)
定义状态机的流转逻辑。这是配置中最核心的部分。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `type_code` | String | 关联的业务类型代码 (需在 `work_types` 中定义) |
| `from_state` | String | 流转的起始状态 |
| `action` | String | 触发流转的操作动作名称 |
| `to_state` | String | 流转的目标状态 |
| `target_owner_strategy` | String | 负责人处理策略 (详见下文) |
| `required_fields` | Array | 执行该动作时，`form_data` 中必须包含的字段列表 |

#### 负责人处理策略 (`target_owner_strategy`)
- `KEEP`: 负责人保持不变。
- `TO_CREATOR`: 负责人变更为事项的最初创建者。
- `TO_SPECIFIC_USER`: 从操作请求的 `form_data` 中提取 `target_owner_id` 作为新负责人。

---

## 3. 配置示例：新增一个“缺陷管理”流程

假设我们要增加一个“缺陷(BUG)”流程，步骤如下：

### 第一步：在 `work_types` 中注册
```json
"work_types": [
  ...
  ["BUG", "缺陷"]
]
```

### 第二步：定义流转规则
在 `workflow_configs` 中添加规则：

```json
{
  "type_code": "BUG",
  "from_state": "DRAFT",
  "action": "REPORT",
  "to_state": "OPEN",
  "target_owner_strategy": "TO_SPECIFIC_USER",
  "required_fields": ["severity", "target_owner_id"]
},
{
  "type_code": "BUG",
  "from_state": "OPEN",
  "action": "FIX",
  "to_state": "RESOLVED",
  "target_owner_strategy": "TO_CREATOR",
  "required_fields": ["solution"]
},
{
  "type_code": "BUG",
  "from_state": "RESOLVED",
  "action": "CLOSE",
  "to_state": "DONE",
  "target_owner_strategy": "KEEP",
  "required_fields": []
}
```

---

## 4. 注意事项

1. **幂等性**：初始化逻辑会检查 `type_code`、`from_state` 和 `action` 的组合，如果数据库已存在相同配置则不会重复插入。
2. **字段一致性**：确保 `workflow_configs` 中引用的 `type_code` 和 `state` 已经在对应的定义列表中存在。
3. **JSON 格式**：修改后请确保 JSON 语法正确，否则初始化会报错并跳过加载。

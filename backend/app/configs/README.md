# 配置说明文档 (Configs README)

本文档详细说明了 `configs/` 目录下配置文件的结构、字段含义以及如何新增配置。

## 1. 配置文件概览

系统采用多文件模块化配置模式，自动加载 `configs/` 目录下所有的 `.json` 文件并进行合并。

- **`global_config.json`**: 存放全局共享配置，如流程状态（`states`）定义。
- **`requirement.json`**: 需求业务（`REQUIREMENT`）的专属配置。
- **`test_case.json`**: 测试用例业务（`TEST_CASE`）的专属配置。

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
定义状态机的流转逻辑。
- **支持格式**: 推荐使用以 `type_code` 为 Key 的对象格式。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `from_state` | String | 流转的起始状态 |
| `action` | String | 触发流转的操作动作名称 |
| `to_state` | String | 流转的目标状态 |
| `target_owner_strategy` | String | 负责人处理策略 (详见下文) |
| `required_fields` | Array | 执行该动作时，必须包含的字段列表 |
| `properties` | Object | 扩展属性（如按钮颜色、权限标识等） |

#### 负责人处理策略 (`target_owner_strategy`)
- `KEEP`: 负责人保持不变。
- `TO_CREATOR`: 负责人变更为事项的最初创建者。
- `TO_SPECIFIC_USER`: 从操作请求中提取 `target_owner_id` 作为新负责人。

---

## 3. 如何新增一个业务流程（以“缺陷 BUG”为例）

1. **创建新文件**: 在 `configs/` 下创建 `bug.json`。
2. **定义类型**:
   ```json
   "work_types": [["BUG", "缺陷"]]
   ```
3. **编写流转规则**:
   ```json
   "workflow_configs": {
     "BUG": [
       {
         "from_state": "DRAFT",
         "action": "REPORT",
         "to_state": "OPEN",
         "target_owner_strategy": "TO_SPECIFIC_USER",
         "required_fields": ["severity", "target_owner_id"],
         "properties": { "button_color": "red" }
       }
     ]
   }
   ```
4. **重启服务**: 初始化逻辑会自动将新配置同步至数据库。

---

## 4. 注意事项

1. **自动同步 (Upsert)**：初始化逻辑会自动更新已有配置或插入新配置。如果你修改了 JSON 中的字段，重启服务后数据库将同步更新。
2. **数据完整性校验**：系统会自动检查 `workflow_configs` 中引用的 `type_code` 和 `state` 是否已定义。若未定义，该条配置将被跳过并记录警告。
3. **JSON 格式**：修改后请确保 JSON 语法正确，否则初始化会报错。

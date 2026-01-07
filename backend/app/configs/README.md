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

---

## 5. 内置业务流程说明

本小节基于当前配置文件，梳理出内置两类业务（需求、测试用例）的完整流转路径，并明确每一步「必须要有备注」和「需要指派人」的规则，便于后续扩展或对齐前端表单。

### 5.1 需求 (`REQUIREMENT`) 流程

**状态主干：**

`DRAFT(草稿)` → `PENDING_REVIEW(待评审)` → `PENDING_DEVELOP(待开发)` → `DEVELOPING(开发中)` → `PENDING_TEST(待测试)` → `PENDING_UAT(待验收)` → `PENDING_RELEASE(待上线)` → `RELEASED(已上线)`

**动作与必填字段：**

- `DRAFT` --`SUBMIT`--> `PENDING_REVIEW`  
  - 需要指派人：`target_owner_id`（评审人）  
  - 必须备注：否  
  - 其他必填：`priority`

- `PENDING_REVIEW` --`APPROVE`--> `PENDING_DEVELOP`  
  - 需要指派人：`target_owner_id`（开发负责人）  
  - 必须备注：`comment`（评审结论 / 说明）

- `PENDING_REVIEW` --`REJECT`--> `DRAFT`  
  - 需要指派人：否（退回给创建人 `TO_CREATOR`）  
  - 必须备注：`comment`（退回原因）

- `PENDING_DEVELOP` --`START`--> `DEVELOPING`  
  - 需要指派人：否（保持当前负责人 `KEEP`）  
  - 必须备注：否

- `DEVELOPING` --`FINISH`--> `PENDING_TEST`  
  - 需要指派人：`target_owner_id`（测试负责人）  
  - 必须备注：否

- `PENDING_TEST` --`PASS`--> `PENDING_UAT`  
  - 需要指派人：`target_owner_id`（验收人 / 业务方）  
  - 必须备注：否

- `PENDING_TEST` --`REJECT`--> `DEVELOPING`  
  - 需要指派人：`target_owner_id`（被打回的开发）  
  - 必须备注：`comment`（缺陷或不通过原因）

- `PENDING_UAT` --`PASS`--> `PENDING_RELEASE`  
  - 需要指派人：`target_owner_id`（发布负责人 / 运维）  
  - 必须备注：否

- `PENDING_UAT` --`REJECT`--> `DEVELOPING`  
  - 需要指派人：`target_owner_id`（被打回的开发）  
  - 必须备注：`comment`（验收不通过原因）

- `PENDING_RELEASE` --`PUBLISH`--> `RELEASED`  
  - 需要指派人：否（保持当前负责人 `KEEP`）  
  - 必须备注：否

> 综上：  
> - **必须填写备注 (`comment`) 的动作**：`REQUIREMENT/PENDING_REVIEW:APPROVE`、`REQUIREMENT/PENDING_REVIEW:REJECT`、`REQUIREMENT/PENDING_TEST:REJECT`、`REQUIREMENT/PENDING_UAT:REJECT`。  
> - **必须指定指派人 (`target_owner_id`) 的动作**：除 `PENDING_REVIEW:REJECT`、`PENDING_DEVELOP:START`、`PENDING_RELEASE:PUBLISH` 外，所有包含 `target_owner_id` 的动作都需要前端提供下拉选择。

---

### 5.2 测试用例 (`TEST_CASE`) 流程

**状态主干：**

`DRAFT(草稿)` → `ASSIGNED(已指派)` → `DEVELOPING(编写中)` → `PENDING_REVIEW(待评审)` → `DONE(已完成)`

**动作与必填字段：**

- `DRAFT` --`ASSIGN`--> `ASSIGNED`  
  - 需要指派人：`target_owner_id`（用例编写人）  
  - 必须备注：否

- `ASSIGNED` --`START_WRITE`--> `DEVELOPING`  
  - 需要指派人：否（保持当前负责任务到编写阶段）  
  - 必须备注：否

- `DEVELOPING` --`SUBMIT_REVIEW`--> `PENDING_REVIEW`  
  - 需要指派人：`target_owner_id`（评审人）  
  - 必须备注：否

- `PENDING_REVIEW` --`APPROVE`--> `DONE`  
  - 需要指派人：否（评审通过后直接完成）  
  - 必须备注：`comment`（评审意见 / 说明）

- `PENDING_REVIEW` --`REJECT`--> `DEVELOPING`  
  - 需要指派人：`target_owner_id`（重新修改用例的人，一般为原作者或指定维护人）  
  - 必须备注：`comment`（不通过原因）

> 综上：  
> - **必须填写备注 (`comment`) 的动作**：`TEST_CASE/PENDING_REVIEW:APPROVE`、`TEST_CASE/PENDING_REVIEW:REJECT`。  
> - **必须指定指派人 (`target_owner_id`) 的动作**：`TEST_CASE/DRAFT:ASSIGN`、`TEST_CASE/DEVELOPING:SUBMIT_REVIEW`、`TEST_CASE/PENDING_REVIEW:REJECT`。

这些约定与前端表单是强绑定关系：  
- 如果某个动作的 `required_fields` 包含 `target_owner_id`，前端必须展示“指派人”选择框；  
- 如果包含 `comment`，前端必须提供备注输入框并在提交前做非空校验。

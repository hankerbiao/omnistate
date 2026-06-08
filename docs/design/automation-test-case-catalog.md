# 自动化测试用例目录（Automation Test Case Catalog）设计

> 版本：v1.0 · 2026-06-05  
> 状态：草案（待评审）  
> 关联文档：[test-case-catalog.md](./test-case-catalog.md)（手工用例目录定稿）  
> 关联模块：`test_specs`、前端「自动化测试用例」(`TestCaseList`)

---

## 1. 背景与目标

### 1.1 现状

| 维度 | 手工用例 (`TestCaseDoc`) | 自动化用例 (`AutomationTestCaseDoc`) |
|------|--------------------------|----------------------------------------|
| 组织方式 | Lab + 多级 `catalog_path`，左树浏览 | 平铺列表，按 `framework` / `status` / 关键词筛选 |
| 目录字段 | `lab_id`、`catalog_path`、`catalog_path_key` | **无** |
| 关联 | `ref_req_id`（可选） | `dml_manual_case_id` → `TestCaseDoc.case_id`（1:1） |
| 入口 | `ManualTestCaseList` + `CatalogTreeSidebar` | `TestCaseList`，无目录 UI |

手工用例目录已在 [test-case-catalog.md](./test-case-catalog.md) 定稿并实现：`TestLabDoc`、`TestCatalogSegmentDoc`、`CatalogService`、左树列表、Creatable 路径编辑等。

自动化用例库当前以 **框架上报 + 脚本元数据** 为主，列表按 `framework` 分组，无法表达：

```text
BIOS / plat_x / release_check / pytest_smoke_login
```

与手工用例 **同一产品线资产树** 下的并列关系。

### 1.2 目标

1. **对齐组织模型**：自动化用例具备与手工用例相同的 Lab + 多级目录语义（深度不限、单路径归属、段名 Creatable）。
2. **统一浏览体验**：自动化列表页采用左树 + 面包屑 + 前缀过滤，与 `ManualTestCaseList` 一致。
3. **保留关联语义**：`dml_manual_case_id` 继续表示与平台手工用例的 1:1 绑定；目录与关联 **正交但可联动**。
4. **兼容上报链路**：框架 `/report` 批量上报时，目录可 **从已关联手工用例继承**，减少人工补录。
5. **复用基础设施**：共享 `TestLabDoc` 与目录规范化逻辑，避免两套 Lab 治理。

### 1.3 非目标（本期不做）

- 段批量重命名/合并（与手工目录一致，P2+ 再议）。
- 按目录套批量下发执行任务（目录先当分类）。
- 手工/自动化目录 **强制同步**（手工改目录不自动改自动化）。
- 废弃 `framework` / `tags` 等现有筛选维度（与目录并存）。

---

## 2. 手工 Lab 与自动化 Lab 的关系

### 2.1 决策：**共享同一套 Lab 树（全局 namespace）**

| 方案 | 说明 | 结论 |
|------|------|------|
| A. 共享 `TestLabDoc` | BIOS/BMC 等产品线 Lab 对手工、自动化均适用 | **推荐 ✓** |
| B. 独立 `AutomationLabDoc` | 两套 Lab 编码、管理页、停用迁移 | 拒绝：治理重复、用户认知分裂 |
| C. Lab 共享、L2+ 完全共享段树 | 同一 Lab 下 segments 仅一套 | 部分采用（见 2.2） |

依据手工目录定稿 **决策 #5「Lab 范围：全局一套」**，自动化用例 **不另建 Lab 集合**。

**展示语义**：

```text
同一 Lab「BIOS」下：
  ├── plat_x / smoke          ← 手工用例叶子
  └── plat_x / auto_regression ← 自动化用例叶子（可与手工同前缀或不同段）
```

### 2.2 L2+ 路径段：**按 scope 隔离统计，Lab 级共享**

手工与自动化在同一 Lab 下 **可能** 使用相同路径段名（如 `plat_x`），也可能各自扩展专属段（如 `auto_ci`）。

**推荐**：在 `TestCatalogSegmentDoc` 增加 **`scope`** 字段：

| 值 | 含义 |
|----|------|
| `manual` | 手工用例 segment 登记（**默认值**，兼容现有数据） |
| `automation` | 自动化用例 segment 登记 |

- **Lab 实体**：完全共享。
- **Segment 建议与树聚合**：按 `scope` 分开计数与 `/catalog/tree` 聚合，避免手工树混入自动化专用段（或反之）。
- **用户仍可在自动化表单输入与手工相同的段名**；登记时写入 `scope=automation` 的 segment 文档，与 `scope=manual` 同名段 **不冲突**（唯一键扩展为 `(lab_id, scope, parent_path, segment_name)`）。

> **默认推荐**：scope 隔离 segment 注册表；Lab 与路径规范化规则与手工完全一致。

---

## 3. 数据模型

### 3.1 `AutomationTestCaseDoc` 扩展字段

在 `automation_test_cases` 集合新增（与 `TestCaseDoc` 对齐）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `lab_id` | string | 是（迁移后） | FK → `TestLabDoc.lab_id` |
| `catalog_path` | string[] | 是（迁移后） | 长度 ≥ 1；段名规范化小写存储 |
| `catalog_path_key` | string | 是（迁移后） | 查询键，如 `plat_x/smoke` |

**不持久化** `catalog_breadcrumb`：列表/详情响应时由 `CatalogService.build_breadcrumb()` 计算（与手工一致）。

**索引建议**（追加）：

```python
IndexModel("lab_id"),
IndexModel("catalog_path_key"),
IndexModel([("lab_id", ASCENDING), ("catalog_path_key", ASCENDING)]),
IndexModel([("dml_manual_case_id", ASCENDING), ("lab_id", ASCENDING)]),
```

**保留字段**（不变）：

- `dml_manual_case_id`：关联 `TestCaseDoc.case_id`（unique）
- `framework`、`automation_type`、`tags`：与目录并存，不作目录替代

### 3.2 `TestCatalogSegmentDoc` 扩展

| 字段 | 类型 | 说明 |
|------|------|------|
| `scope` | string | `manual` \| `automation`，默认 `manual` |

**唯一索引**调整为：`(lab_id, scope, parent_path, segment_name)`。

现有 segment 文档在迁移脚本中补 `scope: "manual"`（或依赖模型默认值）。

### 3.3 `TestLabDoc`

**无结构变更**。Lab 停用/删除逻辑需扩展用例计数与迁移范围（见 §5、§8）。

### 3.4 路径段规范化

**完全复用** `app/modules/test_specs/domain/catalog_path.py`：

1. `strip()` 去空白  
2. 拒绝空串、`/`、`\`、控制字符  
3. 转小写入库  
4. 同 Lab + 同 `parent_path` + 同 `scope` 下段名唯一（大小写不敏感）

---

## 4. 复用 vs 新建

| 组件 | 策略 | 说明 |
|------|------|------|
| `TestLabDoc` / `test_labs` | **复用** | 全局 Lab，管理页 `CatalogLabsPage` 不变 |
| `TestCatalogSegmentDoc` | **扩展 `scope`** | 不新建 `automation_catalog_segments` |
| `CatalogService` | **扩展** | 所有 register/suggestions/tree/count 方法增加 `scope` 参数 |
| `AutomationTestCaseDoc` | **扩展字段** | 不合并进 `TestCaseDoc`（模型职责不同） |
| 独立 Automation Lab API | **不建** | 继续 `/api/v1/catalog/labs` |

**为何不合并 TestCaseDoc / AutomationTestCaseDoc？**

- 生命周期不同：自动化由框架上报 upsert、含 `code_snapshot` / `script_ref`。
- 关联键不同：自动化 1:1 绑定手工 `case_id`。
- 列表与权限虽相近，文档 schema 差异大，合并会提高耦合。

**为何不共用 segment 而不加 scope？**

- 左树 `case_count` 需区分手工/自动化；混计会导致「选中节点数量」误导。
- 自动化-only 段（如 `nightly`）不应出现在手工 Creatable 建议中。

---

## 5. API 变更

### 5.1 Catalog API（扩展 query）

| 方法 | 路径 | 变更 |
|------|------|------|
| GET | `/catalog/suggestions` | 新增 query **`scope`**：`manual`（默认）\| `automation` |
| GET | `/catalog/tree` | 新增 query **`scope`**；树节点 `case_count` 仅统计对应 scope 的用例 |

`CatalogService.build_tree(lab_id, scope)` 聚合：

- segments：`TestCatalogSegmentDoc` where `lab_id` + `scope`
- cases：`TestCaseDoc` 或 `AutomationTestCaseDoc` where `lab_id` + `is_deleted=false`

### 5.2 Lab 生命周期 API（行为扩展）

| 方法 | 变更 |
|------|------|
| GET `/catalog/labs` | `case_count` → **`manual_case_count` + `automation_case_count` + `case_count`（合计）** |
| POST `/catalog/labs/{id}/deactivate` | 迁移 **手工 + 自动化** 用例的 `lab_id` 至 `target_lab_id`；`catalog_path` 不变；分别更新两种 scope 的 segment 计数 |
| DELETE `/catalog/labs/{id}` | 仅当 **手工 + 自动化** 均为 0 可删 |

### 5.3 自动化用例 API

**`GET /automation-test-cases`** 新增 query：

| 参数 | 说明 |
|------|------|
| `lab_id` | 过滤 Lab |
| `catalog_prefix` | JSON 数组，前缀匹配子树（复用 `CatalogService.match_catalog_prefix_filter`） |

保留现有：`framework`、`automation_type`、`status`、`dml_manual_case_id` 等。

**响应投影**（`AutomationTestCaseResponse`）增加：

- `lab_id`、`catalog_path`、`catalog_path_key`
- `lab_name`、`catalog_breadcrumb`（服务端 enrich）

**`POST /automation-test-cases`**（人工创建）：

- Body 增加 **`lab_id`、`catalog_path`**（必填，与手工创建对齐）
- 校验 active Lab；register segment `scope=automation`

**`POST /automation-test-cases/report`**（框架上报）：

- 每条 metadata 落库前：
  1. 解析 `dml_manual_case_id`；
  2. 若关联 `TestCaseDoc` 存在且 **自动化侧尚无目录**（新建或历史无字段）：**默认继承** 手工用例的 `lab_id` + `catalog_path`；
  3. 若已有关联记录且已有目录：**不覆盖**（上报不改动目录，避免 CI 误刷）；
  4. 若无关联手工用例：fallback `LAB-DEFAULT` + `["未分类"]`（与手工迁移策略一致）。

可选 body 字段（P1）：`catalog_path` / `lab_id` 显式覆盖（需 `test_cases:write` 或 report 白名单策略，**默认 P2 再开**）。

**`PUT/PATCH`**（若后续暴露）：目录变更走 `CatalogService.adjust_path_on_update(..., scope="automation")`。

---

## 6. 前端 UX

### 6.1 自动化列表页 `TestCaseList`

对齐 `ManualTestCaseList` 布局：

```text
┌─────────────────┬──────────────────────────────────────────┐
│ CatalogTree     │ 面包屑：BIOS / plat_x / …                │
│ Sidebar         │ 工具栏：搜索、framework/status 筛选、新建  │
│ (scope=auto)    │ 表格：名称、auto_case_id、framework、…    │
│                 │         catalog_breadcrumb、关联手工 ID     │
└─────────────────┴──────────────────────────────────────────┘
```

**状态**：

- `selectedLabId`、`catalogPrefix`（与手工相同）
- 列表请求：`api.listAutomationTestCases({ lab_id, catalog_prefix, ... })`

**组件改动**：

| 组件 | 改动 |
|------|------|
| `CatalogTreeSidebar` | 新增 prop **`catalogScope?: 'manual' \| 'automation'`**，传给 `getCatalogTree` / 刷新 |
| `catalogStyles` | 复用，无变更 |
| `TestCaseList` | 引入 sidebar + 面包屑；表格列增加 `catalog_breadcrumb` |
| `api.ts` | `getCatalogTree` / `getCatalogSuggestions` 增加 `scope`；列表 params 增加目录过滤 |

### 6.2 创建/编辑表单

| 场景 | 行为 |
|------|------|
| 从树「新建」 | `CatalogPathEditor`：`lockLab` + `lockedPrefix` 继承当前选中前缀 |
| 人工创建 | 完整目录块；suggestions 带 `scope=automation` |
| 关联手工用例 | 输入 `dml_manual_case_id` 后 **可选**「从手工用例复制目录」按钮，拉取手工用例详情填充 |
| 框架上报 | 无表单；目录由后端继承（§5.3） |

`CatalogPathEditor` 增加 prop **`catalogScope`**，内部 suggestions API 带 scope。

### 6.3 详情与关联展示

- **关联 Tab**（现有）：展示 `dml_manual_case_id`；若手工用例存在，展示 **手工目录面包屑** 与 **自动化目录面包屑** 对比。
- **路径不一致时**：展示非阻塞提示「与关联手工用例目录不同」（不强制对齐）。

### 6.4 Lab 管理页

- 表格「用例数」拆分为手工 / 自动化 / 合计（或 tooltip）。
- 停用迁移说明文案覆盖两类用例。

---

## 7. 与手工用例关联（`dml_manual_case_id`）

### 7.1 字段语义（保持不变）

`AutomationTestCaseDoc.dml_manual_case_id` ↔ `TestCaseDoc.case_id`（平台业务 ID，1:1 unique）。

上报链路 `_try_link_test_case` 已按 `case_id` 查找手工用例，**不改变关联键**。

### 7.2 目录与关联的关系

| 原则 | 说明 |
|------|------|
| **正交** | 目录回答「自动化资产放在哪」；关联回答「对应哪条手工用例」 |
| **默认继承** | 首次上报/创建且能 link 手工用例时，目录 **默认复制** 手工 `lab_id` + `catalog_path` |
| **允许偏离** | 自动化可放在同 Lab 下不同路径（如手工在 `smoke`，自动化在 `smoke/auto`） |
| **不同步** | 手工用例后续改目录 **不自动更新** 自动化（避免批量误伤；UI 可提示差异） |
| **校验（可选 P2）** | 创建时若 `dml_manual_case_id` 存在，校验手工用例存在；**不强制** 目录相同 |

### 7.3 跨视图导航

- 手工用例详情：已有自动化关联时，展示自动化目录 + 跳转自动化列表（filter by `dml_manual_case_id`）。
- 自动化详情：跳转手工用例详情（按 `case_id`）。

---

## 8. 历史数据迁移

### 8.1 迁移优先级

对 `automation_test_cases` 中缺少 `lab_id` / `catalog_path` 的记录：

| 优先级 | 条件 | 目标目录 |
|--------|------|----------|
| 1 | 存在 `TestCaseDoc` where `case_id = dml_manual_case_id` | 复制手工 `lab_id` + `catalog_path` |
| 2 | 无关联手工用例 | `LAB-DEFAULT` + `["未分类"]`（与 [test-case-catalog.md §7](./test-case-catalog.md) 一致） |

### 8.2 脚本

建议：`backend/scripts/migrate_automation_test_case_catalog.py`

- `--dry-run`
- 确保 `LAB-DEFAULT` 存在（复用现有迁移逻辑）
- 批量 `$set` 目录字段 + 注册 `scope=automation` segments
- 输出：继承手工数 / 默认 Lab 数 / 跳过数

### 8.3 与手工迁移的顺序

**先手工、后自动化**（手工目录必须先就绪，自动化才能继承）。

若手工用例尚未迁移，自动化 fallback 到 DEFAULT，**可在手工迁移后二次脚本**「仅更新仍与手工不一致且可 link 的记录」（可选 `--reconcile-from-manual`）。

### 8.4 Lab 生命周期

`LabService._count_cases` / `_migrate_cases` 扩展包含 `AutomationTestCaseDoc`。

---

## 9. 分期 rollout 与文件清单

### P0 — 后端模型 + 列表过滤 + 迁移（约 3–4 人日）

**目标**：DB 字段就绪；API 可按 Lab/前缀查自动化；历史数据可迁移；report 默认继承目录。

| 层级 | 文件 |
|------|------|
| 模型 | `repository/models/automation_test_case.py` |
| 模型 | `repository/models/test_catalog_segment.py`（`scope`） |
| 领域 | `domain/catalog_path.py`（若无变更则跳过） |
| 服务 | `service/catalog_service.py`（scope 参数、automation tree/count） |
| 服务 | `service/automation_test_case_service.py`（catalog 校验、enrich、list 过滤、report 继承） |
| 服务 | `service/lab_service.py`（计数与迁移含自动化） |
| API | `api/automation_test_case_routes.py` |
| API | `api/catalog_routes.py`（scope query） |
| Schema | `schemas/test_case.py` 或 automation 专用 schema |
| 脚本 | `scripts/migrate_automation_test_case_catalog.py` |
| 测试 | `tests/integration/test_specs/test_automation_case_catalog*.py` |

**验收**：迁移后所有自动化用例有目录；`GET /automation-test-cases?lab_id=&catalog_prefix=` 正确；report 新用例继承手工目录。

### P1 — 前端目录 UX（约 3–4 人日）

**目标**：自动化列表左树 + 面包屑；创建表单目录块；Lab 管理展示双计数。

| 层级 | 文件 |
|------|------|
| 类型 | `frontend/src/types/index.ts` |
| API | `frontend/src/services/api.ts` |
| 组件 | `frontend/src/components/TestCaseList.tsx` |
| 组件 | `frontend/src/components/CreateAutomationTestCaseForm.tsx` |
| 组件 | `frontend/src/components/catalog/CatalogTreeSidebar.tsx` |
| 组件 | `frontend/src/components/catalog/CatalogPathEditor.tsx` |
| 组件 | `frontend/src/components/CatalogLabsPage.tsx` |
| 样式 | `frontend/src/components/catalog/catalogStyles.ts`（按需） |

**验收**：选手工 Lab 与树节点后列表过滤；新建继承前缀；suggestions 与手工互不污染。

### P2 — 体验增强与治理（约 2 人日，可选）

| 内容 | 文件 |
|------|------|
| 手工/自动化目录差异提示 | `TestCaseList.tsx`、手工详情 Modal |
| 从手工复制目录按钮 | `CreateAutomationTestCaseForm.tsx` |
| report 显式 catalog 覆盖 | `automation_test_case_service.py` |
| 文档 | `docs/guide/test-requirements-cases.md` |
| Lab 停用 segment 计数双 scope 校正 | `catalog_service.py` |

---

## 10. 开放问题与默认推荐

| # | 问题 | 默认推荐 |
|---|------|----------|
| 1 | 自动化是否与手工 **强制同 Lab**？ | **否**；默认继承但允许改 Lab |
| 2 | 手工改目录后是否同步自动化？ | **否**；仅 UI 提示差异；提供手动「复制目录」 |
| 3 | 同一 Lab 下 segment 是否共用？ | **名可同，注册按 scope 隔离** |
| 4 | 无关联手工的上报用例目录？ | `LAB-DEFAULT` + `["未分类"]` |
| 5 | 列表主筛选保留 framework 吗？ | **保留**，与目录 **AND** 组合 |
| 6 | report 是否允许覆盖已有目录？ | **否**（P0）；P2 可选显式 flag |
| 7 | 创建自动化是否必填 `dml_manual_case_id`？ | **保持现状**（上报必填；UI 创建视产品，建议 P1 仍可选） |
| 8 | `catalog/tree` 是否提供合并视图？ | **否**；各 scope 独立树；Dashboard 若要总量另做聚合 API |
| 9 | RBAC 是否新增权限？ | **否**；复用 `test_cases:read/write` + `catalog:labs:*` |
| 10 | 迁移后是否强制 API 校验目录必填？ | **是**（与手工 P2 一致）；迁移完成前 feature flag 可短暂放宽 |

---

## 11. 手工 vs 自动化目录对照

| 维度 | 手工用例 | 自动化用例 |
|------|----------|------------|
| 文档模型 | `TestCaseDoc` | `AutomationTestCaseDoc` |
| L1 Lab | 共享 `TestLabDoc` | 共享 `TestLabDoc` |
| L2+ 段登记 | `TestCatalogSegmentDoc` `scope=manual` | 同集合 `scope=automation` |
| 路径字段 | `lab_id`, `catalog_path`, `catalog_path_key` | 同左 |
| 列表页 | `ManualTestCaseList` | `TestCaseList` |
| 左树 API | `GET /catalog/tree?scope=manual` | `GET /catalog/tree?scope=automation` |
| 创建入口 | `CreateTestCaseForm` + `CatalogPathEditor` | `CreateAutomationTestCaseForm` + 同组件 |
| 主要创建方式 | 人工表单 | 框架 **report** + 少量人工 |
| 默认目录来源 | 用户选择 / 树继承 | **继承关联手工** → 否则 DEFAULT |
| 关联字段 | `ref_req_id`（需求，可选） | `dml_manual_case_id`（手工 case_id，1:1） |
| 与关联对象目录关系 | 独立 | 默认同目录，可偏离，不同步 |
| 额外分类维度 | `test_category`, `tags` | `framework`, `automation_type`, `tags` |
| 迁移脚本 | `migrate_test_case_catalog.py` | `migrate_automation_test_case_catalog.py` |
| Lab 停用迁移 | 已支持手工 | 扩展支持自动化 |

---

## 12. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-05 | v1.0 草案：自动化目录对齐手工模型；scope 隔离 segment；分 P0/P1/P2 |

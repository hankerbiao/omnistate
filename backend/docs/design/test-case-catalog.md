# 测试用例目录（Test Case Catalog）设计定稿

> 版本：v1.0 · 2026-06-04  
> 状态：已定稿（待实现）  
> 关联模块：`test_specs`、前端「测试用例」与「Lab 管理」

---

## 1. 背景与目标

当前测试用例以平铺列表 + `test_category` / `tags` 组织，无法表达：

`BIOS / BIOS_for_xxxproject / BIOS_release_check / 具体测试用例`

这类 **多级资产路径**。本设计引入 **Catalog（目录）**：

- **L1 Lab**：管理员全局预设，统一治理产品线/实验室域。
- **L2+ 路径段**：创建/编辑用例时由测试人员 **Creatable 自由追加**，深度 **不固定**。
- **用例**：路径末端叶子，**单归属**（一条路径）。

与 **测试需求 `ref_req_id`** 正交：目录回答「资产放在哪」，需求回答「交付与 workflow」。

---

## 2. 决策记录

### 2.1 已确认（产品输入）

| # | 议题 | 决定 |
|---|------|------|
| 1 | 层级深度 | **允许更深，不限制层数**（Lab 之下 1..N 段路径） |
| 2 | 单/多路径 | **A：只能一条** |
| 3 | 路径语义（业务含义） | 常见中间层含义为 **平台型号**；**不强制**每层叫什么（Suite 等不固定） |
| 4 | — | 中间层命名 **灵活**，不在 UI 写死 Project/Suite 字样 |
| 5 | Lab 范围 | **全局一套** |
| 6 | Lab `code` | **不可改**，仅可改显示名等 |
| 7 | Lab 停用 | **旧用例必须迁移**到其他 Lab |
| 8 | Lab 删除 | **仅当下属 0 条用例** 可删 |
| 9 | Lab 管理权限 | **系统管理员 + TPM** |
| 10 | L2+ 创建方式 | **创建用例时输入即登记**（Creatable） |
| 11 | 去重 | **不区分大小写**；入库统一 **小写** |
| 12 | 字符 | **不允许 `/`** 等路径分隔符出现在段名中 |
| 13 | 命名提示 | **不要** |
| 14 | 必填 | **目录必填**；Lab 必填；**至少 1 个**路径段（层数不固定） |

### 2.2 推荐默认（未单独确认项）

| # | 议题 | 决定 |
|---|------|------|
| 15 | `ref_req_id` | **可选**（目录为主组织方式） |
| 16 | 列表主视图 | **以目录树为主** |
| 17 | L1 展示 | **左侧可展开树**（L1 仅来自 Lab API） |
| 18 | L2+ 管理 | **一期不支持** 段名批量重命名/合并 |
| 19 | 展示 | 列表/详情展示 **完整面包屑** |
| 20 | 按套执行 | **一期不做**；段路径先当分类 |
| 21 | `test_category` | **保留**，与目录并存 |
| 22 | 实施顺序 | ① Lab 管理 → ② 用例表单目录 → ③ 左树列表 → ④ 历史迁移 |
| 23 | 历史数据 | 默认 Lab + 路径 `["未分类"]` |
| 24 | 后端 | **允许** 表结构与 API 变更 |

---

## 3. 概念模型

```text
TestLab (L1, 管理员)
    └── catalog_path[0]      ← 用户段，如「平台型号」层
            └── catalog_path[1]
                    └── … (0..N 段，深度不限)
                            └── TestCase (叶子)
```

**展示路径（面包屑）**：

```text
{lab.display_name} / {segment_1} / {segment_2} / … / {case.title}
```

**存储路径（逻辑键）**：

```text
lab_id + catalog_path[]   # 各段已规范化为小写
```

说明：

- 不对用户暴露「第 2 层叫 Project、第 3 层叫 Suite」；表单统一为 **「目录路径」**，可 **添加一级 / 删除一级**。
- 业务上中间层常表示 **平台型号**，但允许只建 1 段或很多段。

---

## 4. 数据模型

### 4.1 `TestLabDoc`（新建集合 `test_labs`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `lab_id` | string | 主键，如 `LAB-BIOS` |
| `code` | string | 唯一、**创建后不可变**，如 `BIOS` |
| `name` | string | 显示名，可改 |
| `description` | string? | 可选 |
| `sort_order` | int | 排序 |
| `is_active` | bool | 停用前须完成用例迁移 |
| `created_at` / `updated_at` | datetime | |

索引：`code` 唯一；`is_active` + `sort_order`。

### 4.2 `TestCaseDoc`（扩展）

| 字段 | 类型 | 说明 |
|------|------|------|
| `lab_id` | string | 必填，FK → `TestLabDoc.lab_id` |
| `catalog_path` | string[] | 必填，**长度 ≥ 1**；每段规范化后小写存储 |
| `ref_req_id` | string? | **改为可选**（与目录正交） |
| `test_category` | string? | **保留**，不作目录替代 |

索引建议：

- `(lab_id, catalog_path)` — 列表按子树过滤（见 API）
- 保留现有 `ref_req_id` 等索引

**`catalog_path` 在 MongoDB 查询**：子树过滤使用前缀匹配，例如选中路径 `["a","b"]` 时查询：

```python
{"lab_id": lab_id, "catalog_path": {"$all": [{"$elemMatch": ...}]}}  # 或 path 前缀约定
```

推荐实现：**存储时增加冗余字段** `catalog_path_key` = `a/b/c`（段内仍禁止 `/`，仅作查询键），或 `catalog_path` 数组 + `$expr` 前缀比较。实现阶段在 service 层封装 `match_catalog_prefix(lab_id, prefix_segments)`。

### 4.3 `TestCatalogSegmentDoc`（新建集合 `test_catalog_segments`，懒登记）

用于 Creatable 建议与统计，**不是**用例的权威路径来源。

| 字段 | 类型 | 说明 |
|------|------|------|
| `lab_id` | string | |
| `parent_path` | string[] | 父路径（`[]` 表示 Lab 直下第一层） |
| `segment_name` | string | 规范化后小写 |
| `usage_count` | int | 冗余，创建/删除用例时维护 |

唯一键：`(lab_id, parent_path, segment_name)`。

### 4.4 路径段规范化（强制）

创建/更新用例或登记 segment 时，服务端统一：

1. `strip()` 去首尾空白  
2. 拒绝空串、拒绝包含 `/`、`\`、控制字符  
3. **转小写** 后入库（展示可用原始输入或 title-case，**以库内小写为准去重**）  
4. 同 Lab + 同 `parent_path` 下，段名唯一（大小写视为相同）

---

## 5. API 设计（`/api/v1/catalog`）

权限建议：

| 权限 | 角色 |
|------|------|
| `catalog:labs:read` | 登录用户 |
| `catalog:labs:manage` | 系统管理员、TPM |

### 5.1 Lab

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/catalog/labs` | 列表；query `active_only=true` 供用例表单 |
| POST | `/catalog/labs` | 创建；body: `code`, `name`, … |
| PUT | `/catalog/labs/{lab_id}` | 更新 `name`/`description`/`sort_order`；**不可改 `code`** |
| POST | `/catalog/labs/{lab_id}/deactivate` | 停用；body **`target_lab_id`**（必填），迁移全部用例 |
| DELETE | `/catalog/labs/{lab_id}` | 仅 **0 用例** 可删 |

**停用迁移（决策 #7-B）**：

- 事务内：`TestCaseDoc.lab_id = target_lab_id`，`catalog_path` **不变**。
- 同步更新/合并 `TestCatalogSegmentDoc` 计数。
- 源 Lab `is_active = false`。

### 5.2 路径建议（Creatable）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/catalog/suggestions` | query: `lab_id`, `parent_path`（JSON 数组，可选）→ 返回下一层已有段名列表 |
| GET | `/catalog/tree` | query: `lab_id` → 返回该 Lab 下聚合树（由 segments + cases 汇总，供左树） |

### 5.3 测试用例（扩展既有接口）

**创建/更新** `TestCase`：

- 请求增加：`lab_id`, `catalog_path: string[]`（≥1）
- `ref_req_id` 可选
- 校验：`lab_id` 存在且 `is_active`

**列表** `GET /test-cases` 增加 query：

| 参数 | 说明 |
|------|------|
| `lab_id` | 过滤 Lab |
| `catalog_prefix` | JSON 数组，前缀匹配子树 |

响应增加（投影）：

- `lab_id`, `catalog_path`, `catalog_breadcrumb`（服务端拼好显示名）

---

## 6. 前端设计

### 6.1 Lab 管理面板（管理员 + TPM）

- 路由建议：`/settings/catalog-labs` 或系统配置子页。
- 表格：code、显示名、排序、状态、用例数、操作。
- 操作：新建、编辑显示名、停用（**弹窗选择目标 Lab**）、删除（仅 0 用例）。
- **不提供** 用户段（L2+）的编辑；段仅随用例 Creatable 增长。

### 6.2 创建/编辑测试用例 — 「所属目录」

```
Lab *                 [下拉，仅 active]
目录路径 *            [段 1] [段 2] … [+ 添加一级] [- 删除]
                      每段：Creatable Select（suggestions API）
预览                  BIOS / plat_x / release_check
… 其余字段（title、ref_req_id 可选、test_category 保留…）
```

规则：

- 至少 **1** 段；段数不限。
- 选 Lab 后重置 suggestions；每段变更后刷新下一段建议。
- 提交前客户端可做相同规范化预览（最终以服务端为准）。

### 6.3 测试用例管理页

- **左侧**：Lab 列表（来自 API）→ 展开动态子树（`/catalog/tree`）。
- **右侧**：当前选中前缀下的用例表；面包屑顶栏；「新建」继承 `lab_id` + `catalog_prefix`。
- 用例卡片/行：显示完整 `catalog_breadcrumb`；**详情** 按钮（与需求页一致，点击行不强制弹窗）。

### 6.4 与需求页关系

- `RequirementsPage` 仍可按 `ref_req_id` 查看用例；用例行展示目录面包屑。
- 主入口以 **目录树** 为准（决策 #16）。

---

## 7. 历史数据迁移

**策略（#23-C）**：

1. 初始化 Lab：至少 `LAB-DEFAULT` / code `DEFAULT` / 名「默认」。
2. 批量脚本：无 `lab_id` 的用例 → `lab_id = LAB-DEFAULT`，`catalog_path = ["未分类"]`。
3. `ref_req_id` 保持原值；若为空则保持空。

脚本位置建议：`backend/scripts/migrate_test_case_catalog.py`（实现阶段添加）。

---

## 8. 实施分期

| 期 | 内容 | 交付 |
|----|------|------|
| **P1** | Lab CRUD + 停用迁移 + 权限 | 管理面板、API |
| **P2** | `TestCase` 字段 + 校验 + suggestions | 创建/编辑表单目录块 |
| **P3** | `catalog/tree` + 列表左树筛选 | 用例管理主界面 |
| **P4** | 历史迁移脚本 + 文档/索引 | 数据一致 |

**一期不做**：段批量重命名/合并、按目录套批量执行、`test_category` 废弃。

---

## 9. 边界与风险

| 风险 | 缓解 |
|------|------|
| 段名自由导致同义重复（`plat_a` / `plat-a`） | 小写 + 去 `/`；后期可加「相似名提示」 |
| 变长 `catalog_path` 查询性能 | `catalog_path_key` 冗余或数组前缀索引 |
| Lab 停用迁移遗漏 segment 计数 | 迁移与用例变更共用 domain service |
| `ref_req_id` 改可选破坏旧客户端 | API 文档标注；创建表单 UI 标可选 |

---

## 10. 附录：与旧字段对照

| 旧字段 | 新设计 |
|--------|--------|
| `test_category` | 保留，语义为「测试类型标签」，不是目录 |
| `tags` | 保留，交叉检索 |
| `ref_req_id` | 可选；workflow 仍可通过需求绑定 |
| — | `lab_id` + `catalog_path[]` 为目录权威来源 |

---

## 11. 开发计划

详见：[test-case-catalog-implementation-plan.md](./test-case-catalog-implementation-plan.md)

---

## 12. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-06-04 | v1.0 定稿：合并产品确认项与推荐默认项 |
| 2026-06-04 | 增加开发计划链接 |

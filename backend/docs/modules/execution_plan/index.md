# Execution Plan 模块

`execution_plan` 是 DML V4 的**执行计划编排模块**：负责管理手工/自动化用例的执行计划、任务下发、结果回填和进度统计。

## 模块职责（一句话）

用户创建执行计划 → 向计划添加手工/自动化用例 → 手工用例由用户回填结果，自动化用例下发到 execution 引擎执行 → 系统聚合所有执行记录，提供用例级别的执行统计。

## 模块关系

```
test_specs (用例定义层)
     ↓ 引用 case_id / auto_case_id
execution_plan (执行计划编排层)
     ├── manual: 结果存入 ManualExecutionResultDoc
     └── auto: 通过 execution_task_id 关联 ExecutionTaskDoc
                ↓
          execution (任务执行层)
```

- **test_specs**：提供用例定义（`TestCaseDoc` / `AutomationTestCaseDoc`），execution_plan 在添加用例时写入快照字段（`case_title`、`component`、`priority`）。
- **execution**：提供任务执行能力，auto 类型的 plan item 通过 `execution_task_id` 关联到 `ExecutionTaskDoc`。
- **auth**：写操作校验 `execution_tasks:write`，读操作校验 `execution_tasks:read`。

## 核心目录

```
app/modules/execution_plan/
├── api/
│   ├── routes.py              # HTTP 路由入口
│   ├── dependencies.py        # FastAPI 依赖注入
│   └── exception_handler.py   # 业务异常转 HTTP 错误
├── schemas/
│   └── execution_plan.py      # Pydantic 请求/响应结构
├── service/
│   └── execution_plan_service.py  # 核心业务逻辑
├── repository/models/
│   └── execution_plan.py      # Beanie 文档模型
└── domain/
    ├── constants.py           # 枚举与状态映射
    └── exceptions.py          # 领域异常
```

## 核心数据模型

### ExecutionPlanDoc（集合：`execution_plans`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `plan_id` | `str` | 计划业务 ID（格式 `EP-YYYY-NNNNNN`） |
| `title` | `str` | 计划标题 |
| `status` | `str` | `draft` / `active` / `done` / `archived` |
| `item_count` | `int` | 条目总数 |
| `done_count` | `int` | 已完成条目数 |
| `progress_percent` | `int` | 进度百分比 0-100 |

### ExecutionPlanItemDoc（集合：`execution_plan_items`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `item_id` | `str` | 条目 ID |
| `plan_id` | `str` | 所属计划 ID |
| `ref_type` | `str` | `manual`（手工）或 `auto`（自动化） |
| `case_id` | `str` | 用例 ID（manual→`case_id`, auto→`auto_case_id`） |
| `manual_case_id` | `Optional[str]` | auto 条目关联的手工用例 ID |
| `case_title` | `str` | 用例标题快照 |
| `assignee_id` | `Optional[str]` | 执行人 |
| `status` | `str` | `pending` / `running` / `done` / `fail` |
| `execution_task_id` | `Optional[str]` | 关联的自动化执行任务 ID |
| `result_id` | `Optional[str]` | 关联的手工执行结果 ID |
| `archived_at` | `Optional[datetime]` | 归档时间 |

### ManualExecutionResultDoc（集合：`manual_execution_results`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `result_id` | `str` | 结果 ID |
| `item_id` | `str` | 关联的条目 ID |
| `case_id` | `str` | 手工用例 ID |
| `passed` | `bool` | 通过/失败 |
| `notes` | `str` | 备注 |
| `severity` | `str` | 严重程度 |
| `actual` / `expected` | `str` | 实际/预期结果 |
| `env` | `str` | 测试环境 |
| `executed_by` | `str` | 执行人 |
| `executed_at` | `datetime` | 执行时间 |

## 自动化用例执行统计设计方案

### 背景

在用例看板（TestCaseBoard）和用例详情弹窗（TestCaseDetailModal / AutomationCaseDetailModal）中，需要展示某个测试用例的历史执行统计，包括手工执行和自动化执行的总次数、通过数、失败数、通过率。

### 统计口径

统计来源**同时覆盖**手工执行和自动化执行：

```
总执行次数 = 手工执行结果数 + 自动化执行任务数（状态为 PASSED/DONE）
```

- **手工部分**：查询 `ManualExecutionResultDoc`，按 `case_id` 聚合
- **自动化部分**：查询 `ExecutionPlanItemDoc`（`case_id` + `ref_type=auto` + `execution_task_id != null`）→ 关联 `ExecutionTaskDoc`，统计 `overall_status` 为 `PASSED` 或 `DONE` 的条数

### API 端点

```
GET /api/v1/execution-plans/cases/{case_id}/execution-stats
```

### 返回结构

```json
{
  "case_id": "TC-001",
  "total": 15,
  "passed": 12,
  "failed": 3,
  "pass_rate": 80.0,
  "last_executed_at": "2026-06-15T10:30:00",
  "recent": [
    {
      "result_id": "R-001",
      "passed": true,
      "executed_by": "user_01",
      "executed_at": "2026-06-15T10:30:00",
      "plan_id": "EP-2026-000001",
      "notes": ""
    }
  ]
}
```

### 调用链

```
前端（用例看板 / 详情弹窗）
  └─ GET /cases/{case_id}/execution-stats
       └─ ExecutionPlanService.get_case_execution_stats(case_id)
            ├─ ManualExecutionResultDoc.find(case_id) → 手工结果列表
            ├─ ExecutionPlanItemDoc.find(case_id + ref_type=auto + task_id != null) → 关联的任务 ID
            ├─ ExecutionTaskDoc.find(task_ids) → 获取任务状态
            └─ 合并计数 + 计算通过率 + 取最近 10 条手工记录
```

### 前端展示

- **TestCaseDetailModal**（手工用例详情）：`执行统计` tab 页，展示总次数/通过/失败/通过率 4 个统计卡片，及最近执行记录列表
- **AutomationCaseDetailModal**（自动化用例详情）：打开时自动加载执行统计
- **TestCaseBoardDetail**（用例看板详情）：`StatsContent` 组件，同时适配手工和自动化用例

## 自动化与手工用例关联方案

### 背景

自动化测试用例（`AutomationTestCaseDoc`）和手工测试用例（`TestCaseDoc`）之间存在对应关系：一个手工用例可能有一个对应的自动化用例来覆盖相同的测试场景。通过关联，用户可以在手工用例看板中看到对应的自动化执行状态，反之亦然。

### 数据模型

关联是**双向**的：

```
TestCaseDoc                         AutomationTestCaseDoc
  └─ linked_auto_case_id: str?         └─ linked_manual_case_id: str
     (关联的自动化用例 ID)                 (关联的手工用例 ID)
```

- `AutomationTestCaseDoc.linked_manual_case_id`：默认空字符串 `""`，唯一稀疏索引
- `TestCaseDoc.linked_auto_case_id`：默认 `None`，稀疏索引

### 关联/解除 API

**建立关联**：`POST /api/v1/test-cases/{case_id}/automation-link`

请求体：
```json
{
  "auto_case_id": "auto_001",
  "version": "v1.0"
}
```

**解除关联**：`DELETE /api/v1/test-cases/{case_id}/automation-link`

### 关联逻辑（双向写入）

```
link_automation_case(case_id, auto_case_id):
  1. 查找手工用例 TestCaseDoc 和自动化用例 AutomationTestCaseDoc
  2. 如果自动化用例已关联其他手工用例 → 清除旧关联
  3. 如果手工用例已关联其他自动化用例 → 清除旧关联
  4. 建立双向关联：
     case_doc.linked_auto_case_id = auto_case_id
     auto_doc.linked_manual_case_id = case_id
  5. 保存两个文档
```

解除关联同理，双向清空。

### 幂等性与冲突处理

- 旧关联自动清理，不会因为双向关联而产生"一个用例被多个用例引用"的状态
- `linked_manual_case_id` 的唯一稀疏索引在数据库层面防止了并发冲突
- 关联操作记录审计日志，`action = "LINK_AUTOMATION"`

### 关联后的业务效果

| 场景 | 效果 |
|------|------|
| 自动化用例详情 | 显示"关联手工用例"区域，展示关联的手工用例 ID 和跳转链接 |
| 手工用例详情 | 显示"自动化覆盖"区域，展示关联的自动化用例状态 |
| 执行计划添加 | 添加自动化用例到计划时，自动解析 `linked_manual_case_id` 填入 `manual_case_id` 字段，用于执行统计聚合 |
| 用例看板 | 统一展示执行统计，同时覆盖手工和自动化结果 |

### 自动化框架侧关联

自动化执行框架在通过 `/automation-test-cases/report` 上报用例元数据时，也可以设置 `linked_manual_case_id`。后端收到后会自动尝试查找对应 `TestCaseDoc` 并建立关联。详见 `AutomationTestCaseService._try_link_test_case()`。

## API 路由总览

路由前缀：`/api/v1/execution-plans`

### 计划查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/items/my-items` | 我的任务列表 |
| GET | `/items` | 查询条目列表（按状态/计划） |
| GET | `/items/overview` | 全部计划执行概览 |
| GET | `/items/{item_id}` | 条目详情 |
| GET | `/items/archived` | 归档箱 |

### 手工结果

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/items/{item_id}/result` | 提交手工执行结果 |
| GET | `/items/{item_id}/result` | 获取手工执行结果 |
| GET | `/cases/{case_id}/execution-stats` | 用例执行统计 |

### 自动化下发

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/items/{item_id}/dispatch` | 下发单个自动化用例 |
| POST | `/items/batch-dispatch` | 批量下发自动化用例 |
| POST | `/items/{item_id}/cancel-execution` | 取消自动化执行 |
| POST | `/items/{item_id}/rerun` | 重置为待执行（支持可选执行人变更） |
| POST | `/items/{item_id}/re-execute` | 重新执行（保留旧结果历史） |

### 计划 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/plans` | 计划列表 |
| POST | `/plans` | 创建计划 |
| GET | `/plans/{plan_id}` | 计划详情 |
| PUT | `/plans/{plan_id}` | 更新计划 |
| DELETE | `/plans/{plan_id}` | 删除计划 |
| POST | `/plans/{plan_id}/items` | 向计划添加用例 |
| DELETE | `/plans/{plan_id}/items/{item_id}` | 从计划移除用例 |
| PUT | `/plans/{plan_id}/items/{item_id}` | 更新条目（执行人/状态等） |
| PUT | `/plans/{plan_id}/items/batch-assignee` | 批量更新执行人 |

### 归档管理

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | `/items/{item_id}/archive` | 归档条目 |
| PUT | `/items/{item_id}/unarchive` | 取消归档 |

## 关键调用链

| 场景 | 调用链 |
|------|--------|
| 手工执行结果回填 | API → `ExecutionPlanService.submit_result()` → 创建 `ManualExecutionResultDoc` + 更新 item 状态 |
| 自动化用例下发 | API → `ExecutionPlanService.dispatch_item()` → `ExecutionTaskCommandService.create_task()` |
| 重新执行（rerun） | API → `ExecutionPlanService.rerun_item()` → 重置 status=pending + 清 task_id（可选更新 assignee） |
| 用例执行统计 | API → `ExecutionPlanService.get_case_execution_stats()` → 聚合手工 + 自动化结果 |
| 自动化关联手工 | API → `TestCaseCommandService.link_automation_case()` → `TestCaseService.link_automation_case()` → 双向写入 |

## 常见修改场景

| 需求 | 优先文件 |
|------|----------|
| 改计划/条目字段 | `schemas/execution_plan.py`、`repository/models/execution_plan.py` |
| 改执行统计逻辑 | `service/execution_plan_service.py` 的 `get_case_execution_stats()` |
| 改自动化/手工关联 | `app/modules/test_specs/service/test_case_service.py` 的 `link_automation_case()` |
| 改重新执行行为 | `service/execution_plan_service.py` 的 `rerun_item()` |
| 新增计划状态 | `domain/constants.py` 的 `PlanStatus` / `PlanItemStatus` |

## 风险点

- 执行统计的自动化部分通过 `ExecutionPlanItemDoc.execution_task_id` 间接关联 `ExecutionTaskDoc`，如果任务被软删除，统计会遗漏。当前 `cancel_execution()` 会软删除任务，统计查询时需要注意。
- 自动化/手工关联是双向的，修改一侧时需同步更新另一侧，否则会导致索引冲突或数据不一致。
- `PlanItemRerunRequest` 的 `assignee_id` 字段仅用于重置条目执行人，不会自动下发任务到执行引擎。用户需手动点击"执行"按钮。

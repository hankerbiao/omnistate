# 项目（Project）模块设计文档

> 文档路径：`backend/docs/modules/project/design.md`  
> 设计目标：引入"项目"作为顶层容器，支持测试用例/测试执行/工作项等多对多关联，统计时按项目聚合。

---

## 1. 需求概述

### 1.1 背景

当前系统缺少"项目"维度。测试用例、测试执行计划、工作项等实体独立存在，无法按项目维度进行：
- 数据隔离与分类
- 统计与报表聚合
- 权限范围控制（未来可扩展）

### 1.2 核心需求

1. **项目作为独立实体**：可创建、编辑、归档项目
2. **多对多关联**：一个测试用例可以关联多个项目；一个项目可以包含多个测试用例/计划/任务
3. **按项目统计**：聚合统计项目下的用例数、执行计划数、任务数、完成率等
4. **现有数据兼容**：已有数据需要平滑过渡（可批量关联默认项目）

---

## 2. 数据模型设计

### 2.1 项目实体（ProjectDoc）

```python
class ProjectDoc(Document):
    """项目文档模型"""

    project_id: Indexed(str, unique=True)  # 格式: PRJ-2026-00001
    key: Indexed(str, unique=True)        # 短标识: "RED-FISH-V3"
    name: str                              # 显示名称: "Redfish V3 测试项目"
    description: Optional[str] = None
    status: str = "active"              # active | archived
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = False

    class Settings:
        name = "projects"
        indexes = [
            IndexModel("project_id", unique=True),
            IndexModel("key", unique=True),
            IndexModel("status"),
            IndexModel("is_deleted"),
        ]
```

### 2.2 关联字段扩展（多对多）

在现有实体上新增 `project_ids: list[str]` 字段，表示该实体关联的项目列表。

| 集合 | 新增字段 | 说明 |
|------|---------|------|
| `test_cases` | `project_ids: list[str] = []` | 测试用例可跨项目复用 |
| `automation_test_cases` | `project_ids: list[str] = []` | 自动化用例同理 |
| `test_requirements` | `project_ids: list[str] = []` | 测试需求归属 |
| `execution_plans` | `project_ids: list[str] = []` | 执行计划归属（通常1个） |
| `execution_tasks` | `project_ids: list[str] = []` | 从计划/请求透传 |
| `bus_work_items` | `project_ids: list[str] = []` | 工作项关联 |
| `test_case_collections` | `project_ids: list[str] = []` | 测试集归属 |

> **不添加 project_ids 的集合**：`execution_plan_items`（通过 plan 关联）、`execution_task_cases`（通过 task 关联）、`manual_execution_results`（通过 item 关联）——避免数据冗余，通过父级间接关联。

---

## 3. 模块架构

### 3.1 目录结构

```
backend/app/modules/project/
├── api/
│   ├── __init__.py              # re-export router
│   ├── routes.py                # FastAPI 路由
│   └── dependencies.py          # Service Depends 工厂
├── service/
│   ├── __init__.py
│   └── project_service.py       # 业务逻辑 + 聚合统计
├── repository/
│   └── models/
│       ├── __init__.py
│       └── project.py             # ProjectDoc Beanie 模型
├── schemas/
│   └── __init__.py
│   └── project.py                 # Pydantic 请求/响应模型
└── domain/
    └── constants.py             # 项目状态常量
```

### 3.2 分层职责

| 层级 | 职责 | 关键文件 |
|------|------|---------|
| **API** | 路由注册、参数解析、依赖注入、返回 `APIResponse` | `api/routes.py` |
| **Service** | 业务逻辑、ID生成、关联聚合查询、软删除清理 | `service/project_service.py` |
| **Repository** | Beanie 模型定义、索引、hooks | `repository/models/project.py` |
| **Schemas** | Pydantic 请求/响应模型校验 | `schemas/project.py` |

---

## 4. API 设计

### 4.1 项目 CRUD

```
GET    /api/v1/projects
       查询参数: name(模糊), status, key, page, page_size, sort_by, sort_order
       响应: APIResponse[{ items: [...], total: N }]

POST   /api/v1/projects
       请求: { name, key, description, status }
       响应: APIResponse[ProjectResponse]

GET    /api/v1/projects/:project_id
       响应: APIResponse[ProjectDetailResponse] (含统计字段)

PUT    /api/v1/projects/:project_id
       请求: { name?, description?, status? }
       响应: APIResponse[ProjectResponse]

DELETE /api/v1/projects/:project_id
       软删除，同步清理关联实体的 project_ids
       响应: APIResponse[None]
```

### 4.2 项目统计

```
GET    /api/v1/projects/:project_id/stats
       响应: APIResponse[ProjectStatsResponse]
```

统计内容：
```json
{
  "test_case_count": 120,
  "auto_case_count": 80,
  "requirement_count": 15,
  "plan_count": 5,
  "task_count": 42,
  "task_done_count": 30,
  "task_progress": 71.4,
  "collection_count": 3
}
```

### 4.3 关联实体筛选

现有实体的列表 API 增加 `project_id` 查询参数：

```
GET /api/v1/test-cases?project_id=PRJ-2026-00001
GET /api/v1/execution-plans?project_id=PRJ-2026-00001
GET /api/v1/execution-tasks?project_id=PRJ-2026-00001
GET /api/v1/work-items?project_id=PRJ-2026-00001
GET /api/v1/test-case-collections?project_id=PRJ-2026-00001
```

MongoDB 查询条件：`{ "project_ids": { "$in": [project_id] }, "is_deleted": false }`

---

## 5. ID 生成策略

### 5.1 project_id

格式：`PRJ-YYYY-XXXXX`
- `PRJ-`：固定前缀
- `YYYY`：当前年份
- `XXXXX`：5位数字，按年递增，不足补零

生成逻辑：
```python
async def _generate_project_id(self) -> str:
    year = datetime.utcnow().year
    prefix = f"PRJ-{year}-"
    # 查询当年最大序号
    last = await ProjectDoc.find(
        {"project_id": {"$regex": f"^{prefix}"}},
        sort=[("project_id", -1)]
    ).limit(1).to_list()
    seq = 1
    if last:
        seq = int(last[0].project_id.split("-")[-1]) + 1
    return f"{prefix}{seq:05d}"
```

### 5.2 key（短标识）

由用户创建时指定，如 `"RED-FISH-V3"`，需唯一校验。用于 URL 友好、快捷引用。

---

## 6. Service 层设计

### 6.1 ProjectService 核心方法

```python
class ProjectService(BaseService):

    async def list_projects(
        self, *,
        name: str | None = None,
        status: str | None = None,
        key: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        ...

    async def create_project(
        self, data: dict[str, Any], created_by: str | None = None,
    ) -> ProjectDoc:
        ...

    async def get_project(self, project_id: str) -> ProjectDoc | None:
        ...

    async def update_project(
        self, project_id: str, data: dict[str, Any],
    ) -> ProjectDoc:
        ...

    async def delete_project(self, project_id: str) -> None:
        """软删除，并清理所有关联实体的 project_ids"""
        ...

    async def get_project_stats(self, project_id: str) -> dict[str, Any]:
        """聚合统计项目下的各类实体数量"""
        ...
```

### 6.2 删除时的关联清理

```python
async def delete_project(self, project_id: str) -> None:
    doc = await ProjectDoc.find_one(
        {"project_id": project_id, "is_deleted": False}
    )
    if not doc:
        raise ValueError(f"Project not found: {project_id}")

    # 1. 软删除项目本身
    doc.is_deleted = True
    doc.updated_at = datetime.utcnow()
    await doc.save()

    # 2. 清理所有关联实体的 project_ids（避免残留脏数据）
    collections = [
        TestCaseDoc, AutomationTestCaseDoc, TestRequirementDoc,
        ExecutionPlanDoc, ExecutionTaskDoc, BusWorkItemDoc,
        TestCaseCollectionDoc,
    ]
    for model in collections:
        await model.find(
            {"project_ids": project_id}
        ).update_many({"$pull": {"project_ids": project_id}})
```

---

## 7. 关联实体修改范围

### 7.1 测试规格模块（test_specs）

| 文件 | 修改内容 |
|------|---------|
| `test_specs/repository/models/test_case.py` | `project_ids: list[str] = []` |
| `test_specs/repository/models/automation_test_case.py` | `project_ids: list[str] = []` |
| `test_specs/repository/models/test_requirement.py` | `project_ids: list[str] = []` |
| `test_specs/api/routes.py` | 列表查询增加 `project_id` 参数 |
| `test_specs/schemas/test_case.py` | 请求/响应增加 `project_ids` 字段 |
| `test_specs/service/test_case_service.py` | 保存时校验 project_ids 存在性 |

### 7.2 执行计划模块（execution_plan）

| 文件 | 修改内容 |
|------|---------|
| `execution_plan/repository/models/execution_plan.py` | `project_ids: list[str] = []` |
| `execution_plan/schemas/execution_plan.py` | `CreatePlanRequest` / `UpdatePlanRequest` 增加 `project_ids` |
| `execution_plan/service/execution_plan_service.py` | 创建/更新时透传 project_ids |
| `execution_plan/api/routes.py` | 列表查询增加 `project_id` 参数 |

### 7.3 执行模块（execution）

| 文件 | 修改内容 |
|------|---------|
| `execution/repository/models/execution_task.py` | `project_ids: list[str] = []` |
| `execution/schemas/execution_task.py` | 请求/响应增加 `project_ids` |
| `execution/api/routes.py` | 列表查询增加 `project_id` 参数 |

> 注：任务下发时，若执行计划携带 `project_ids`，任务创建时透传到 `ExecutionTaskDoc`。

### 7.4 工作流模块（workflow）

| 文件 | 修改内容 |
|------|---------|
| `workflow/repository/models/work_item.py` | `project_ids: list[str] = []` |
| `workflow/api/routes_items.py` | 列表查询增加 `project_id` 参数 |
| `workflow/schemas/work_item.py` | 请求/响应增加 `project_ids` |

### 7.5 测试集模块（test_case_collection）

| 文件 | 修改内容 |
|------|---------|
| `test_case_collection/repository/models/collection.py` | `project_ids: list[str] = []` |
| `test_case_collection/api/routes.py` | 列表查询增加 `project_id` 参数 |
| `test_case_collection/schemas/collection.py` | 请求/响应增加 `project_ids` |

---

## 8. 前端设计

### 8.1 新增页面：ProjectsPage

路径：`frontend/src/components/ProjectsPage.tsx`

布局模式：分栏布局（参照 `CatalogLabsPage` / `RoleManagement`）

```
┌─────────────────────────────────────────────────┐
│ 项目列表                    [+ 新建项目]          │
├────────────────┬────────────────────────────────┤
│                │                                │
│ 搜索框          │  项目详情                       │
│ 状态过滤        │  ────────────────────────────   │
│                │  名称 / Key / 描述              │
│ - Project A    │  状态: active                   │
│ - Project B    │                                │
│ - Project C    │  统计面板                       │
│                │  ┌────┐ ┌────┐ ┌────┐ ┌────┐  │
│                │  │用例│ │计划│ │任务│ │完成│  │
│                │  │120 │ │  5 │ │ 42 │ │71% │  │
│                │  └────┘ └────┘ └────┘ └────┘  │
│                │                                │
│                │  关联实体列表（Tab 切换）        │
│                │  - 测试用例  - 执行计划  - 任务 │
│                │                                │
└────────────────┴────────────────────────────────┘
```

### 8.2 前端文件清单

| 文件 | 说明 |
|------|------|
| `frontend/src/components/ProjectsPage.tsx` | 项目列表/详情页面 |
| `frontend/src/types/index.ts` | 新增 `Project`, `ProjectStats`, `CreateProjectRequest`, `UpdateProjectRequest` |
| `frontend/src/services/api.ts` | 新增 `listProjects`, `createProject`, `updateProject`, `deleteProject`, `getProjectStats` |
| `frontend/src/config/navigation.ts` | 新增 `projects` 导航项（放在"测试资产"分组） |
| `frontend/src/App.tsx` | 新增 `projects` page case |
| `frontend/src/components/AppShell.tsx` | 新增 `PAGE_TITLES` 映射 |

### 8.3 现有页面增强

| 页面 | 增强内容 |
|------|---------|
| `TestExecutionPlanDemo.tsx` | 顶部增加项目筛选下拉框；计划详情显示关联项目 |
| `RequirementsPage.tsx` | 需求列表增加项目筛选；详情显示关联项目 |
| `CatalogLabsPage.tsx` | 用例详情增加"关联项目"多选器 |
| `TestCaseCollectionPage.tsx` | 测试集详情增加项目筛选/关联 |

---

## 9. RBAC 权限设计

新增权限码：

| 权限码 | 描述 | 默认角色 |
|--------|------|---------|
| `projects:read` | 查看项目列表和详情 | ADMIN, TPM, REVIEWER, QA, TESTER |
| `projects:write` | 创建、更新项目 | ADMIN, TPM |
| `projects:delete` | 删除项目 | ADMIN |

修改 `scripts/init/init_rbac.py`：
- 在 `DEFAULT_PERMISSIONS` 中新增上述 3 个权限
- 在 `DEFAULT_ROLES` 中为 `ADMIN` 分配全部 3 个，`TPM` 分配 `read` + `write`

---

## 10. 数据迁移与初始化

### 10.1 初始化脚本

新增 `scripts/init/init_projects.py`：

```python
async def init_default_project():
    """初始化默认项目，将现有无 project_ids 的数据关联到默认项目"""
    default = await ProjectDoc.find_one({"key": "DEFAULT"})
    if not default:
        default = ProjectDoc(
            project_id="PRJ-2026-00001",
            key="DEFAULT",
            name="默认项目",
            description="系统自动创建的默认项目，用于承载历史数据",
            status="active",
        )
        await default.insert()

    # 批量为历史数据添加默认项目关联（可选）
    # 通过命令行参数控制是否执行历史数据迁移
```

### 10.2 运行方式

```bash
# 开发环境：初始化默认项目
python scripts/init/init_projects.py --migrate-existing

# 生产环境：仅创建默认项目，不迁移历史数据（由管理员手动归档）
python scripts/init/init_projects.py
```

### 10.3 现有索引迁移

新增 `project_ids` 字段的集合需要添加 MongoDB 索引：
```python
IndexModel("project_ids")  # 支持 $in 查询
```

在 `scripts/init/init_mongodb.py` 或启动时通过 `SKIP_INDEX_SYNC=0` 自动同步。

---

## 11. 实施阶段建议

### Phase 1：项目模块本身（基础 CRUD）

- [ ] 创建 `project` 模块（模型、API、Service、Schemas）
- [ ] 注册路由、Beanie 模型、导航
- [ ] 前端 `ProjectsPage` 页面
- [ ] RBAC 权限初始化
- [ ] 初始化默认项目脚本

### Phase 2：关联实体添加 project_ids（逐个模块）

- [ ] 测试规格模块（TestCaseDoc, AutomationTestCaseDoc, TestRequirementDoc）
- [ ] 执行计划模块（ExecutionPlanDoc）
- [ ] 执行模块（ExecutionTaskDoc）
- [ ] 工作流模块（BusWorkItemDoc）
- [ ] 测试集模块（TestCaseCollectionDoc）

每个模块的修改范围：
1. 模型新增 `project_ids` 字段 + 索引
2. Schema 新增 `project_ids` 字段
3. API 列表查询增加 `project_id` 参数
4. Service 创建/更新时透传/校验 `project_ids`
5. 前端详情页增加"关联项目"选择器

### Phase 3：统计功能

- [ ] 后端 `get_project_stats` 聚合查询
- [ ] 前端项目详情页统计面板（图表、进度条）
- [ ] 现有页面（执行计划、用例管理）增加项目筛选

### Phase 4：数据迁移（可选）

- [ ] 运行 `init_projects.py --migrate-existing` 将历史数据关联默认项目
- [ ] 管理员在 UI 中手动重新分配项目

---

## 12. 关键文件清单（修改 + 新增）

### 后端新增

```
backend/app/modules/project/
├── api/
│   ├── __init__.py
│   ├── routes.py
│   └── dependencies.py
├── service/
│   ├── __init__.py
│   └── project_service.py
├── repository/
│   └── models/
│       ├── __init__.py
│       └── project.py
├── schemas/
│   └── __init__.py
│   └── project.py
└── domain/
    └── constants.py
backend/scripts/init/init_projects.py
```

### 后端修改

```
backend/app/shared/infrastructure/bootstrap.py      # 注册 PROJECT_DOCUMENT_MODELS
backend/app/shared/api/main.py                    # 注册 project_router
backend/scripts/init/init_rbac.py                 # 新增项目权限
```

### 前端新增

```
frontend/src/components/ProjectsPage.tsx
```

### 前端修改

```
frontend/src/types/index.ts                       # 新增 Project 类型
frontend/src/services/api.ts                      # 新增项目 API 方法
frontend/src/config/navigation.ts                 # 新增 projects 导航项
frontend/src/App.tsx                              # 新增 page case
frontend/src/components/AppShell.tsx               # 新增 PAGE_TITLES
```

---

## 13. 注意事项

1. **索引性能**：`project_ids` 字段需要 MongoDB 索引（`IndexModel("project_ids")`），否则 `$in` 查询在大数据量下性能差。
2. **事务一致性**：MongoDB 4.0+ 支持多文档事务，但 Beanie 对事务的支持有限。项目删除时清理关联的 `project_ids` 采用批量 `update_many`，非原子操作，但可接受（最终一致）。
3. **Key 唯一性**：`key` 字段用户可指定，需要严格唯一校验。建议在 API 层校验后再写入。
4. **前端多选器**：关联项目使用多选组件（类似 Tag 输入），支持搜索已有项目。推荐在项目详情页用 Tab 切换展示关联的各类实体。
5. **向后兼容**：已有数据无 `project_ids` 字段，在 MongoDB 中空数组默认不存在，查询时 `$in` 匹配空列表不会返回结果。Phase 4 迁移可解决此问题。

---

## 14. 附录：API 响应示例

### 创建项目

```json
POST /api/v1/projects
{
  "name": "Redfish V3 测试项目",
  "key": "RED-FISH-V3",
  "description": "Redfish 协议 V3 版本的测试覆盖"
}

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "project_id": "PRJ-2026-00001",
    "key": "RED-FISH-V3",
    "name": "Redfish V3 测试项目",
    "description": "Redfish 协议 V3 版本的测试覆盖",
    "status": "active",
    "created_by": "admin",
    "created_at": "2026-06-17T09:00:00Z",
    "updated_at": "2026-06-17T09:00:00Z"
  }
}
```

### 项目统计

```json
GET /api/v1/projects/PRJ-2026-00001/stats

Response:
{
  "code": 0,
  "message": "ok",
  "data": {
    "test_case_count": 120,
    "auto_case_count": 80,
    "requirement_count": 15,
    "plan_count": 5,
    "task_count": 42,
    "task_done_count": 30,
    "task_progress": 71.4,
    "collection_count": 3
  }
}
```

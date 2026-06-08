# 用例集合（TestCaseCollection）设计文档

## 概述

用例集合是一个用户可以自定义命名的逻辑分组，用于将不同目录、不同 Lab 的测试用例聚合到同一集合中，方便在创建执行任务时快速选取。

---

## 数据模型

### TestCaseCollectionDoc

```python
from datetime import datetime
from typing import Optional, List
from beanie import Document, before_event, Save, Insert
from pydantic import Field

class TestCaseCollectionDoc(Document):
    """用例集合 - Beanie ODM"""
    collection_id: str = Field(..., description="集合唯一 ID，如 CC-001")
    name: str = Field(..., description="集合名称")
    description: Optional[str] = Field(None, description="集合说明/描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    case_ids: List[str] = Field(default_factory=list, description="包含的用例 ID (test_case.case_id)")
    auto_case_ids: List[str] = Field(default_factory=list, description="包含的自动化用例 ID")
    created_by: str = Field(..., description="创建人 user_id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @before_event(Save)
    def _set_updated_at(self):
        self.updated_at = datetime.utcnow()

    class Settings:
        name = "test_case_collections"
        use_state_management = True
```

---

## 模块结构

```
backend/app/modules/test_case_collection/
├── __init__.py
├── api/
│   ├── __init__.py           # 导出 collection_router
│   ├── routes.py             # CRUD 路由聚合
│   └── dependencies.py       # Depends 注入
├── schemas/
│   ├── __init__.py           # 门面导出
│   └── collection.py         # Pydantic 请求/响应 Schema
├── service/
│   ├── __init__.py           # 门面导出
│   ├── collection_service.py # 业务逻辑
│   └── exceptions.py         # 领域异常
└── repository/
    └── models/
        ├── __init__.py       # 导出 Doc + DOCUMENT_MODELS
        └── collection.py     # Beanie Document
```

---

## API 设计

### CRUD 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/collections` | 创建集合 |
| GET | `/api/v1/collections` | 列表查询（支持 name/tags 搜索） |
| GET | `/api/v1/collections/{id}` | 集合详情（含所有用例的标题快照） |
| PUT | `/api/v1/collections/{id}` | 更新名称/描述/标签 |
| DELETE | `/api/v1/collections/{id}` | 删除集合 |

### 用例管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/collections/{id}/cases` | 批量添加用例（传入 case_id 列表） |
| DELETE | `/api/v1/collections/{id}/cases` | 批量移除用例 |

### 搜索端点（复用全局搜索模式）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/collections/search?q=xxx` | 搜索集合（名称/描述/标签匹配），用于任务创建时的快速选择 |

---

## 前端页面

### 1. 集合管理页（TestCaseCollectionPage）

```
┌───────────────────────────────────────────────────────────┐
│  PageHero: 用例集合                                        │
│  ┌───────────────────────────────────────────────────────┐│
│  │  [+ 新建集合] [搜索集合...]                            ││
│  ├───────────────────────────────────────────────────────┤│
│  │ ┌────────────────────────────────────────┐            ││
│  │ │ CC-001  回归基线集合                     │  2 个用例 ││
│  │ │ 每次发版前需要回归验证的核心用例集合        │  ← 跳到详情│
│  │ ├────────────────────────────────────────┤           ││
│  │ │ CC-002  性能基准集合                     │  5 个用例 ││
│  │ │ 存储/网络/CPU 性能基线测试                │           ││
│  │ └────────────────────────────────────────┘           ││
│  └───────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────┘
```

### 2. 集合详情页（侧滑面板或独立页面）

```
┌───────────────────────────────────────────────────┐
│  CC-001 · 回归基线集合                              │
│  描述: 每次发版前需要回归验证的核心用例集合            │
│  标签: [回归] [冒烟] [P0]                           │
│  创建人: admin · 更新: 2026-06-08                   │
│                                                    │
│  [+ 添加用例] [批量移除]                             │
│                                                    │
│  TC-001  内存读写压力测试    内存验证组  手动  [移除]│
│  TC-002  内存边界值校验      内存验证组  手动  [移除]│
│  TC-010  安全权限验证        平台质量组  手动  [移除]│
│                                                    │
│  ── 关联自动化用例 ──                                │
│  AC-001  mem_stress_test    pytest      [移除]      │
│  AC-002  mem_boundary_test  pytest      [移除]      │
└───────────────────────────────────────────────────┘
```

### 3. 任务创建时集成（复用现有下发流程的 Step 1）

在下发流程的 Step 1（选择用例）中，增加一个 **"搜索集合"** 入口：

```
  ┌─ 搜索集合 ──────────────────────────────────┐
  │ [回归]     🔍  ────────────────               │
  │                                              │
  │ CC-001  回归基线集合          2 个用例   [+ 添加]│
  │ CC-002  性能基准集合          5 个用例   [+ 添加]│
  └──────────────────────────────────────────────┘
```

点击 `[+ 添加]` 后，集合中的所有用例被批量勾选到用例列表中。

---

## 与现有 DispatchWorkflow 的集成

在 `DispatchWorkflow.tsx` 的 Step 1（select-cases）中：

1. 在"全选"按钮下方增加一行 **"从用例集合添加"** 搜索输入框
2. 输入文本后调用 `GET /api/v1/collections/search?q=xxx` 获取匹配的集合
3. 点击集合 → 将集合中的 `case_ids` 合并到 `selectedCaseIds` 中
4. 已有重复的 case_id 自动去重

无需创建新页面，修改 DispatchWorkflow 组件即可。

---

## 后端搜索实现（与全局搜索一致）

参考 `modules/search/service/search_service.py` 的 `$regex` 模式：

```python
async def search_collections(self, query: str, limit: int = 10):
    pattern = re.escape(query)
    return await TestCaseCollectionDoc.find(
        {"$or": [
            {"name": {"$regex": pattern, "$options": "i"}},
            {"description": {"$regex": pattern, "$options": "i"}},
            {"tags": {"$regex": pattern, "$options": "i"}},
        ]}
    ).limit(limit).to_list()
```

---

## 分步实施优先级

| 步骤 | 内容 | 预估文件 |
|------|------|---------|
| 1 | 后端 CRUD（模型 + Schema + Service + API） | 10 个文件 |
| 2 | 集合搜索 API + 注册到 `shared/api/main.py` | +2 行 |
| 3 | 前端集合管理页 | 1 个页面组件 |
| 4 | DispatchWorkflow 集成（Step 1 中加集合搜索） | 1 个组件修改 |
| 5 | API 注册 + Bootstrap 中注册 Doc 模型 | +2 行 |

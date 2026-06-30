# 操作审计日志模块

> 本文档覆盖 DML V4 系统中操作审计日志的架构、配置、接口和使用方式。

## 目录

1. [架构总览](#1-架构总览)
2. [数据模型](#2-数据模型)
3. [审计范围](#3-审计范围)
4. [配置](#4-配置)
5. [API 接口](#5-api-接口)
6. [AI 输出反馈](#6-ai-输出反馈)
7. [查询示例](#7-查询示例)

---

## 1. 架构总览

审计日志系统通过 **应用层中间件（AuditLogMiddleware）** 实现，在两个中间件之间插入：

```
RequestLoggingMiddleware   ← 生成 request_id / trace_id
         ↓
AuditLogMiddleware         ← 记录操作审计日志
         ↓
Auth 依赖注入              ← 注入 OperationContext（actor_id/username/roles）
```

### 设计原则

1. **不阻塞请求**：审计日志通过 `asyncio.create_task` 异步写入 MongoDB
2. **自动推断**：从 URL 路径自动推断操作类型（action）和资源类型（resource_type）
3. **敏感字段脱敏**：password / api_key / token / secret 自动替换为 `***REDACTED***`
4. **只记写操作**：仅记录 POST/PUT/PATCH/DELETE，GET 默认跳过
5. **自动过期**：90 天 TTL 索引，无需手动清理

### 相关核心代码

- 审计中间件：`shared/middleware/audit_log.py`
- 文档模型：`modules/audit/repository/models/audit_log.py`
- 查询服务：`modules/audit/service/audit_service.py`
- API 路由：`modules/audit/api/routes.py`

---

## 2. 数据模型

### AuditLogDoc（`audit_logs` 集合）

每条记录代表一次用户写操作：

| 字段 | 类型 | 说明 |
|------|------|------|
| `actor_id` | str (Indexed) | 操作者用户 ID |
| `actor_type` | str | 操作者类型: human（默认）/ ai（预留） |
| `username` | str | 操作者用户名 |
| `role_ids` | list[str] | 操作者角色列表 |
| `client_ip` | str | 客户端 IP |
| `request_id` | str | 请求 ID（关联 TraceContext） |
| `method` | str | HTTP 方法 |
| `path` | str | 请求路径 |
| `query_params` | dict | 查询参数 |
| `action` | str | 操作类型（自动推断） |
| `resource_type` | str | 资源类型（自动推断） |
| `resource_id` | str\|null | 资源 ID |
| `request_body` | dict\|null | 请求体（敏感字段已脱敏） |
| `status_code` | int | 响应状态码 |
| `duration_ms` | int | 耗时（毫秒） |
| `created_at` | datetime | 记录时间 |

### 索引

| 索引 | 用途 |
|------|------|
| `actor_id` | 按用户查询 |
| `resource_type` | 按资源类型筛选 |
| `action` | 按操作类型筛选 |
| `(actor_id, -created_at)` | 用户操作历史时间排序 |
| `(resource_type, resource_id)` | 按资源查询 |
| `created_at` TTL (90天) | 自动过期清理 |

---

## 3. 审计范围

### 记录的操作

所有写操作（POST/PUT/PATCH/DELETE）自动记录，跳过健康检查和文档路径。

### 操作类型自动推断

从 HTTP 方法推断默认操作类型：

| 方法 | 默认操作 |
|------|---------|
| POST | `create` |
| PUT | `update` |
| PATCH | `update` |
| DELETE | `delete` |

路径后缀可覆盖操作类型：

| 路径后缀 | 操作类型 |
|---------|---------|
| `.../dispatch` | `dispatch` |
| `.../assign` | `assign` |
| `.../transition` | `transition` |
| `.../ai/polish` | `ai_polish` |
| `.../ai/generate-cases` | `ai_generate_cases` |
| `.../ai/review-case` | `ai_review_case` |
| `.../ai/recommend-cases` | `ai_recommend_cases` |
| `.../failure-analysis/analyze` | `ai_analyze` |

### 资源类型自动推断

从 URL 路径前缀自动识别（17 种业务路径）：

| 路径前缀 | 资源类型 |
|---------|---------|
| `/api/v1/requirements` | `requirement` |
| `/api/v1/test-cases` | `test_case` |
| `/api/v1/execution/tasks` | `execution_task` |
| `/api/v1/execution-plans` | `execution_plan` |
| `/api/v1/collections` | `test_case_collection` |
| `/api/v1/projects` | `project` |
| `/api/v1/auth/users` | `user` |
| `/api/v1/ai/...` | `ai_*`（按具体端点） |

资源 ID 自动从路径参数提取（如 `/api/v1/test-cases/TC-001` → `TC-001`）。

### 不记录的情况

- 健康检查路径（`/health/*`）
- 文档路径（`/docs`、`/openapi.json`、`/redoc`）
- GET 请求（不记录）
- 请求体超过 4KB 时，不记录 `request_body`
- 未认证请求（`actor_id` 为默认值 `-`）

### 敏感字段脱敏

`password` / `api_key` / `token` / `secret`（不区分大小写）的值自动替换为 `***REDACTED***`，嵌套 dict 也会递归处理。

---

## 4. 配置

审计日志配置在中间件中硬编码，无需运行时管理：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| TTL 过期 | 90 天 | MongoDB 自动过期 |
| 最大请求体 | 4KB | 超过不记录 |
| 脱敏字段 | `password`, `api_key`, `token`, `secret` | 不区分大小写 |
| 记录方法 | POST/PUT/PATCH/DELETE | GET 跳过 |

---

## 5. API 接口

### 5.1 查询审计日志

**端点**: `GET /api/v1/audit-logs`

**参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `actor_id` | str | 否 | 操作者 ID |
| `resource_type` | str | 否 | 资源类型 |
| `resource_id` | str | 否 | 资源 ID |
| `action` | str | 否 | 操作类型 |
| `method` | str | 否 | HTTP 方法 |
| `start_time` | datetime | 否 | 开始时间 |
| `end_time` | datetime | 否 | 结束时间 |
| `page` | int | 否 | 页码（默认 1） |
| `page_size` | int | 否 | 每页数量（默认 50，最大 200） |

**权限**: `system:config`

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "...",
        "actor_id": "user-001",
        "username": "张三",
        "method": "POST",
        "path": "/api/v1/test-cases/TC-001",
        "action": "update",
        "resource_type": "test_case",
        "resource_id": "TC-001",
        "request_body": { "title": "登录测试" },
        "status_code": 200,
        "duration_ms": 120,
        "created_at": "2026-06-30T17:35:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  }
}
```

### 5.2 审计日志统计

**端点**: `GET /api/v1/audit-logs/stats`

**权限**: `system:config`

**响应示例**:
```json
{
  "code": 0,
  "data": {
    "total": 1250,
    "by_action": { "create": 800, "update": 350, "delete": 50, "dispatch": 30, "ai_generate_cases": 20 },
    "by_resource_type": { "test_case": 500, "requirement": 200, "execution_plan": 100, "ai_generate_cases": 20 },
    "top_actors": [
      { "actor_id": "user-001", "username": "张三", "count": 450 }
    ]
  }
}
```

---

## 6. AI 输出反馈

AI 输出反馈记录用户对 AI 生成/评审/分析结果的采纳、拒绝或编辑行为。

### 数据模型（`ai_feedback` 集合）

| 字段 | 类型 | 说明 |
|------|------|------|
| `ai_endpoint` | str | AI 端点路径 |
| `request_id` | str | 关联的请求 ID |
| `actor_id` | str | 操作者 ID |
| `input_summary` | str | 输入摘要 |
| `output_summary` | str | 输出摘要 |
| `feedback` | str | accepted / rejected / edited |
| `edited_content` | str\|null | 用户编辑后的内容 |
| `comment` | str | 用户评论 |
| `rating` | int\|null | 评分 1-5 |
| `created_at` | datetime | 记录时间 |

### 提交反馈

**端点**: `POST /api/v1/audit-logs/ai-feedback`

```json
{
  "ai_endpoint": "/ai/generate-cases",
  "feedback": "accepted",
  "input_summary": "生成登录测试用例",
  "output_summary": "5 条登录相关用例",
  "rating": 4
}
```

### 查询反馈统计

**端点**: `GET /api/v1/audit-logs/ai-feedback`

```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 42,
    "stats": { "accepted": 30, "rejected": 8, "edited": 4 }
  }
}
```

用于持续改进 AI 提示词质量：采纳率低的端点需要优化 prompt，被拒绝的内容可作为 prompt 修正的负样本。

---

## 7. 查询示例

### 查某个用户今天干了什么

```
GET /api/v1/audit-logs?actor_id=user-001&start_time=2026-06-30T00:00:00&page_size=200
```

### 查某条用例被修改过几次

```
GET /api/v1/audit-logs?resource_type=test_case&resource_id=TC-001
```

### 查 AI 生成用例的采纳率

```
GET /api/v1/audit-logs/ai-feedback?ai_endpoint=/ai/generate-cases
```

### 查系统配置被谁改了

```
GET /api/v1/audit-logs?resource_type=system_config&action=update
```

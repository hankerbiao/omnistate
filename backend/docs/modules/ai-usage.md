# AI 功能模块使用说明

> 本文档覆盖 DML V4 系统中所有 AI 相关功能的架构、配置、接口和使用方式。

## 目录

1. [架构总览](#1-架构总览)
2. [配置指南](#2-配置指南)
3. [共享 AI 客户端（AIClient）](#3-共享-ai-客户端aiclient)
4. [AI 端点清单](#4-ai-端点清单)
5. [端点详解](#5-端点详解)
   - [5.1 文本润色](#51-文本润色-post-aipolish)
   - [5.2 步骤分析](#52-步骤分析-post-aianalyze-steps)
   - [5.3 需求→用例生成](#53-需求用例生成-post-aigenerate-cases)
   - [5.4 用例评审](#54-用例评审-post-aireview-case)
   - [5.5 智能用例选择](#55-智能用例选择-post-airecommend-cases)
   - [5.6 失败根因分析](#56-失败根因分析-post-failure-analysisanalyze)
   - [5.7 用例集分析](#57-用例集分析-post-ai-analyze-collectionsid)
6. [前端集成](#6-前端集成)
7. [扩展指南](#7-扩展指南)

---

## 1. 架构总览

### 1.1 层级结构

```
shared/ai/client.py         ← AIClient 单例（统一入口）
shared/ai/prompts.py        ← Prompt 模板（版本化管理）
modules/system_config/api/ai_routes.py  ← AI 路由（润色/步骤分析/生成/评审/推荐）
modules/failure_analysis/api/routes.py  ← 失败根因分析路由
modules/ai_analysis/        ← 用例集分析服务
```

### 1.2 核心设计原则

1. **统一入口**：所有业务模块必须通过 `AIClient.get_instance()` 调用 LLM，不允许直接 `OpenAI(...)`
2. **配置热加载**：AI 配置存储在 MongoDB `system_configs` 集合，5 分钟 TTL 缓存，支持运行时修改
3. **调用审计**：每次 LLM 调用记录 model/elapsed_ms/token usage
4. **自动重试**：指数退避重试（最多 3 次）
5. **LLM 无关**：使用 OpenAI 兼容 SDK，`base_url` 可配，兼容 Ollama/OpenAI/任意兼容 API

### 1.3 技术栈

| 组件 | 技术 |
|------|------|
| LLM SDK | `openai` Python SDK |
| 默认 LLM | Ollama (`http://localhost:11434/v1`, 模型 `qwen2.5:latest`) |
| 配置存储 | MongoDB `system_configs` 集合 |
| 配置缓存 | 内存 TTL 缓存（5 分钟） |
| 后端框架 | FastAPI |
| 路由前缀 | `/api/v1/ai`（除 failure-analysis 外） |

相关核心代码：

- 共享客户端：[shared/ai/client.py](../shared/ai/client.py)
- Prompt 模板：[shared/ai/prompts.py](../shared/ai/prompts.py)
- AI 路由：[modules/system_config/api/ai_routes.py](../modules/system_config/api/ai_routes.py)
- 配置服务：[modules/system_config/service/config_service.py](../modules/system_config/service/config_service.py)

---

## 2. 配置指南

### 2.1 AI 配置项

所有 AI 运行时可配置项存储在 MongoDB `system_configs` 集合，通过前端「系统配置」页面或 API 修改。

| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `ai.base_url` | `http://localhost:11434/v1` | LLM API 地址 |
| `ai.model` | `qwen2.5:latest` | 模型名称 |
| `ai.api_key` | `""` | API Key（Ollama 本地不需要） |
| `ai.enabled` | `true` | 是否启用 AI 功能 |
| `ai.temperature` | `0.7` | LLM 温度参数 |
| `ai.max_tokens` | `2048` | 最大输出 Token 数 |
| `ai.timeout` | `60` | 请求超时时间（秒） |
| `ai.max_cases` | `100` | 分析时最大处理用例数 |

### 2.2 启动初始化

系统启动时自动补全缺失的 AI 配置项（`ConfigService.init_default_configs()`）。

如需手动初始化：

```bash
cd backend
python -c "
import asyncio
from app.modules.system_config.service.config_service import ConfigService
asyncio.run(ConfigService.init_default_configs())
"
```

### 2.3 热加载

修改配置后无需重启服务。配置变更会在下次读取时生效（TTL 缓存 5 分钟）。
也可调用 `POST /api/v1/system-configs/reload` 手动清除缓存。

---

## 3. 共享 AI 客户端（AIClient）

`AIClient` 是所有 AI 功能的统一入口单例，位于 `app/shared/ai/client.py`。

### 3.1 基本使用

```python
from app.shared.ai.client import AIClient

client = AIClient.get_instance()

# 方式一：直接获取 content 字符串
content = await client.simple_chat(
    system_prompt="你是测试专家",
    user_content="分析这个用例",
)

# 方式二：获取完整调用信息（含 token 用量、耗时、模型名）
result = await client.chat_completion(
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
    ],
)
print(result.content)      # LLM 返回内容
print(result.model)        # 使用的模型
print(result.elapsed_ms)   # 耗时（毫秒）
print(result.usage)        # token 用量

# 方式三：解析 JSON 响应（自动清理 markdown 代码块）
data = await client.chat_completion_json(
    system_prompt="以 JSON 返回",
    user_content="分析数据",
)
```

### 3.2 配置控制

```python
config = await client.get_config()
# 返回: {"enabled": true, "base_url": "...", "model": "...", ...}

openai_client = await client.get_client()
# 返回 OpenAI 实例或 None（未启用时）
# 配置变更时自动重建实例
```

### 3.3 重试机制

- 最多重试 3 次
- 指数退避：1s → 2s → 4s
- 所有异常都会触发重试
- 超过重试次数后抛出最后一次异常

### 3.4 扩展新功能

新增 AI 端点只需：

```python
from app.shared.ai.client import AIClient

client = AIClient.get_instance()
content = await client.simple_chat(
    system_prompt=YOUR_SYSTEM_PROMPT,
    user_content=build_user_prompt(...),
)
```

不要直接 `from openai import OpenAI`。

---

## 4. AI 端点清单

| 端点 | 方法 | 功能 | 模块 | 前端组件 |
|------|------|------|------|---------|
| `/api/v1/ai/polish` | POST | 文本润色 | `system_config` | `AIPolishButton` |
| `/api/v1/ai/analyze-steps` | POST | 步骤分析 | `system_config` | `TestCaseStepEditorV2` |
| `/api/v1/ai/generate-cases` | POST | 需求→用例生成 | `system_config` | `AiCaseDraftPanel` |
| `/api/v1/ai/review-case` | POST | 用例评审 | `system_config` | `AiCaseReviewPanel` |
| `/api/v1/ai/recommend-cases` | POST | 智能用例选择 | `system_config` | `AiRecommendCasesPanel` |
| `/api/v1/failure-analysis/analyze` | POST | 失败根因分析 | `failure_analysis` | `FailureAnalysisPage` |
| `/api/v1/ai-analyze/collections/{id}` | POST | 用例集分析 | `ai_analysis` | `AIAnalysisPanel` |
| `/api/v1/system-configs/ai/test-connection` | POST | LLM 连接测试 | `system_config` | 系统配置页 |

---

## 5. 端点详解

### 5.1 文本润色 `POST /ai/polish`

**功能**：使用 AI 润色中文技术文档文本。

**请求体**：

```json
{ "text": "需要润色的文本" }
```

**响应体**：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "polished": "润色后的文本"
  }
}
```

**提示词**：`POLISH_SYSTEM_PROMPT` — 中文技术文档润色助手，保持原意不加解释。

**前端集成**：`AIPolishButton` 组件，传入 `text` 和 `onPolished` 回调。

---

### 5.2 步骤分析 `POST /ai/analyze-steps`

**功能**：AI 分析测试用例步骤的完整性和质量，返回评分、问题列表、整体评价。

**请求体**：

```json
{
  "steps": [
    { "step_id": "step-1", "name": "打开页面", "action": "访问 /login", "expected": "页面加载完成" }
  ],
  "title": "用例标题",
  "category": "functional",
  "pre_condition": "前置条件",
  "post_condition": "后置条件"
}
```

**响应体**：

```json
{
  "code": 0,
  "data": {
    "score": 85,
    "totalSteps": 1,
    "issues": [
      {
        "stepIndex": 0,
        "severity": "warning",
        "category": "completeness",
        "field": "expected",
        "message": "预期结果过于简略"
      }
    ],
    "summary": "用例基本完整"
  }
}
```

**评审标准**：
- `error`：步骤名/操作/预期结果为空
- `warning`：描述过短（<10字）/预期不可验证/缺少边界条件
- `suggestion`：可补充数据/细化步骤/增加异常路径

**Prompt**：`STEP_ANALYSIS_SYSTEM_PROMPT` + `STEP_ANALYSIS_USER_TEMPLATE`

---

### 5.3 需求→用例生成 `POST /ai/generate-cases`

**功能**：AI 根据需求自动生成测试用例草稿。两种模式：
- 传 `requirement_id`：从数据库读取需求信息
- 传 `requirement_text`：直接使用提供文本

**请求体**：

```json
{
  "requirement_id": "TR-2026-000001",
  "max_cases": 5
}
```

**响应体**：

```json
{
  "code": 0,
  "data": {
    "cases": [
      {
        "title": "正常登录测试",
        "priority": "P1",
        "test_category": "functional",
        "pre_condition": "用户已注册",
        "post_condition": "退出登录",
        "steps": [
          { "step_id": "step-1", "name": "打开登录页", "action": "访问 /login", "expected": "页面加载完成" }
        ],
        "tags": ["登录", "认证"],
        "rationale": "验证正常登录流程"
      }
    ],
    "reason": ""
  }
}
```

**生成规则**：
- 正常流程用例约占 40%、边界条件约 35%、异常场景约 25%
- 每条用例 3-8 个步骤
- 优先级不应高于关联需求的优先级
- 如果需求信息不足，返回 `{ "cases": [], "reason": "原因说明" }`

**提示词**：`GENERATE_CASES_SYSTEM_PROMPT` + `GENERATE_CASES_USER_TEMPLATE`

---

### 5.4 用例评审 `POST /ai/review-case`

**功能**：AI 从四个维度评审单条测试用例，返回评分、verdict、缺失场景、优先级建议。

**请求体**：

```json
{ "case_id": "TC-MEM-001" }
```

**响应体**：

```json
{
  "code": 0,
  "data": {
    "score": 78,
    "verdict": "needs_revision",
    "dimensions": {
      "completeness": { "score": 80, "issues": ["缺少边界条件测试"] },
      "clarity": { "score": 90, "issues": [] },
      "traceability": { "score": 60, "issues": ["未关联需求"] },
      "executability": { "score": 82, "issues": ["前置条件不够具体"] }
    },
    "missing_scenarios": ["异常输入测试", "边界值测试"],
    "priority_suggestion": "P1",
    "summary": "用例基本可用，但需补充边界条件和异常路径。"
  }
}
```

**评审维度**：
1. `completeness`（完整性）：步骤是否覆盖完整流程
2. `clarity`（清晰度）：步骤描述是否清晰可执行
3. `traceability`（可追溯性）：是否关联需求
4. `executability`（可执行性）：前置条件是否充分

**verdict 判定**：
- `pass`：用例质量合格
- `needs_revision`：需要修改后评审
- `reject`：存在严重问题，建议重写

**提示词**：`REVIEW_CASE_SYSTEM_PROMPT` + `REVIEW_CASE_USER_TEMPLATE`

---

### 5.5 智能用例选择 `POST /ai/recommend-cases`

**功能**：AI 根据变更描述和候选用例列表，推荐应执行的测试用例。

**请求体**：

```json
{
  "project_id": "PROJ-1",
  "change_description": "修改了登录接口的 session 处理逻辑",
  "case_ids": ["TC-001", "TC-002"],
  "max_recommend": 20
}
```

**响应体**：

```json
{
  "code": 0,
  "data": {
    "recommended": [
      { "case_id": "TC-001", "reason": "直接覆盖变更模块", "priority_order": 1 }
    ],
    "excluded": [
      { "case_id": "TC-002", "reason": "与变更无关" }
    ],
    "coverage_note": "覆盖了变更模块的核心功能，可能遗漏兼容性测试。",
    "estimated_runtime_min": 45
  }
}
```

**推荐原则**：
- 优先选择与变更直接相关的用例
- 包含受影响模块的回归用例
- 包含历史失败率较高的用例
- P0/P1 用例优先推荐
- priority_order 从 1 开始，越小越优先

---

### 5.6 失败根因分析 `POST /failure-analysis/analyze`

**功能**：AI 分析测试执行失败的根本原因，返回根因分类、置信度、修复建议。

**请求体**：

```json
{
  "task_id": "TASK-001",
  "case_id": "TC-001",
  "execution_log": "AssertionError: expected 200 got 500",
  "failure_info": "HTTP 500 Internal Server Error",
  "env_info": "Python 3.12, Redis 7.0"
}
```

**响应体**：

```json
{
  "code": 0,
  "data": {
    "root_cause_category": "code_defect",
    "confidence": 0.85,
    "analysis": "登录接口在并发场景下产生竞态条件",
    "probable_cause": "Redis session 写入缺少分布式锁",
    "fix_suggestions": [
      "在 session 写入逻辑中增加分布式锁",
      "增加 session 写入重试机制"
    ],
    "related_patterns": ["并发场景下的资源竞争"],
    "severity": "high"
  }
}
```

**根因分类**：

| 类别 | 说明 |
|------|------|
| `code_defect` | 被测代码有 bug |
| `environment` | 测试环境配置/版本问题 |
| `test_case` | 用例步骤/预期/数据有误 |
| `test_data` | 测试数据不完整或脏数据 |
| `infrastructure` | 网络/存储/计算资源问题 |
| `unknown` | 信息不足 |

---

### 5.7 用例集分析 `POST /ai-analyze/collections/{id}`

**功能**：AI 分析预置用例集的质量、冗余度和覆盖率。

**请求体**：

```json
{
  "analysis_types": ["quality", "redundancy", "coverage"]
}
```

**响应体**：

```json
{
  "code": 0,
  "data": {
    "collection_id": "COL-001",
    "overall_score": 85,
    "quality": { "score": 80, "issues": [...] },
    "redundancy": { "score": 90, "duplicates": [...] },
    "coverage": { "score": 75, "gaps": ["缺少边界值测试"] },
    "recommendations": ["建议补充异常场景"]
  }
}
```

---

## 6. 前端集成

### 6.1 API 方法

所有 AI API 通过 `api.ts` 封装：

```typescript
import { api } from '../../services/api';

// 文本润色
const { data } = await api.aiPolish(text);

// 步骤分析
const res = await api.analyzeTestSteps({ steps, title });

// 生成用例
const res = await api.generateCases({ requirement_id: id });

// 用例评审
const res = await api.reviewCase(caseId);

// 智能推荐
const res = await api.recommendCases({ change_description: desc });

// 失败分析
const res = await api.analyzeFailure({ task_id, case_id });

// 用例集分析
const res = await api.analyzeCollection(collectionId);

// 连接测试
const res = await api.testAIConnection({ base_url, model });
```

### 6.2 类型定义

- `types/ai.ts` — 所有 AI 端点的请求/响应类型
- `types/index.ts` — AI 分析相关类型 + FailureAnalysisDashboard 系列类型

### 6.3 UI 组件

| 组件 | 用途 |
|------|------|
| `AIPolishButton` | 文本润色按钮 |
| `TestCaseStepEditorV2` | 步骤编辑器（含 AI 步骤分析） |
| `AiCaseDraftPanel` | 用例生成草稿预览面板 |
| `AiCaseReviewPanel` | 用例评审面板 |
| `AiRecommendCasesPanel` | 智能用例推荐面板 |
| `AIAnalysisPanel` | 用例集分析面板 |
| `FailureAnalysisPage` | 失效分析页面（含 AI 根因分析） |

---

## 7. 扩展指南

### 7.1 新增一个 AI 端点

1. 在 `shared/ai/prompts.py` 添加 Prompt 模板常量
2. 在 `ai_routes.py`（或对应模块路由）添加新的端点
3. 在 `api.ts` 添加前端 API 方法
4. 在 `types/ai.ts` 添加对应类型
5. 在 `tests/unit/ai/` 添加单元测试

### 7.2 路由注册

AI 路由通过 `app/modules/system_config/api/__init__.py` 自动注册到 `router_registry`。

```python
# 在 api/__init__.py 中
from app.modules.system_config.api.ai_routes import router as ai_router
register_router(ai_router, prefix="/api/v1/ai", tags=["AI Tools"])
```

### 7.3 测试示例

```python
from app.shared.ai.client import AIClient

async def test_ai_endpoint():
    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value={"key": "value"})
        get_instance.return_value = client

        response = await your_ai_endpoint(request)
        assert response.data.key == "value"
```

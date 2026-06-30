# DML V4 — AI 赋能设计文档

> 日期：2026-06-30  
> 状态：规划中，P0 执行中

## 1. 现状

### 1.1 已有 AI 能力

| 能力 | 端点 | 模块 | 状态 |
|------|------|------|------|
| 用例集分析（质量/冗余/覆盖） | `POST /ai-analyze/collections/{id}` | `ai_analysis` | 完整 |
| 文本润色 | `POST /ai/polish` | `system_config` | 完整 |
| LLM 连接测试 | `POST /system-configs/ai/test-connection` | `system_config` | 完整 |
| 配置热加载 | MongoDB `system_configs` + 5min TTL | `system_config` | 完整 |
| 步骤完整性检查 | 无（纯前端规则引擎） | 前端 `TestCaseStepEditorV2` | 完整 |

### 1.2 LLM 接入方式

- 使用 `openai` Python SDK，`base_url` 可配置
- 默认指向本地 Ollama（`http://localhost:11434/v1`，模型 `qwen2.5:latest`）
- 兼容 OpenAI / 任意 OpenAI 兼容 API
- 配置存储在 MongoDB `system_configs` 集合，支持热加载（5 分钟 TTL 缓存）

### 1.3 已知缺口

| 缺口 | 说明 |
|------|------|
| AI 步骤分析端点缺失 | 前端 `TestCaseStepEditorV2` 调用 `POST /ai/analyze-steps`，后端 404 |
| AI 客户端重复创建 | `AIService` 和 `ai_routes.py` 各自独立创建 `OpenAI` client |
| 无调用审计 | AI 调用无 token 用量、耗时、结果记录 |
| 无 Prompt 版本管理 | 提示词硬编码在代码中 |

---

## 2. 路线图

### P0 — 立即补全（前端已就绪，后端缺失）

#### 2.1 共享 AIClient 封装

**目标**：消除 `AIService` 和 `ai_routes.py` 中重复的 OpenAI client 创建逻辑。

**落点**：`backend/app/shared/ai/client.py`

**职责**：
- 统一创建 `OpenAI` 客户端，从 `ConfigService.get_ai_config()` 读取配置
- 内置重试机制（指数退避，最多 3 次）
- 内置超时控制（从配置读取，默认 60s）
- 调用审计日志（token 用量、耗时、模型名）
- 提供 `chat_completion()` 和 `simple_chat()` 两个便捷方法

**接口设计**：

```python
class AIClient:
    """共享 AI 客户端，所有 AI 功能统一入口。"""

    _instance: AIClient | None = None

    @classmethod
    def get_instance(cls) -> AIClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_client(self) -> OpenAI | None:
        """获取 OpenAI 客户端，ai.enabled=false 时返回 None。"""

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """调用 LLM，返回 {content, usage, model, elapsed_ms}。"""

    async def simple_chat(
        self,
        system_prompt: str,
        user_content: str,
        **kwargs,
    ) -> str:
        """简化调用，直接返回 content 字符串。"""
```

**审计日志模型**：`AiCallLogDoc`，存储到 `ai_call_logs` 集合。

#### 2.2 AI 步骤分析端点

**目标**：补全前端已调用的 `POST /ai/analyze-steps`。

**落点**：`backend/app/modules/system_config/api/ai_routes.py`（扩展现有 AI 路由）

**请求体**：

```python
class AnalyzeTestStepsRequest(BaseModel):
    title: str
    category: str = ""
    pre_condition: str = ""
    post_condition: str = ""
    steps: list[dict[str, Any]]  # [{name, action, expected, ...}]
```

**响应体**：

```python
class StepAnalysisIssue(BaseModel):
    step_index: int
    field: str  # name / action / expected
    severity: str  # error / warning / suggestion
    message: str
    proposed_value: str | None = None

class StepAnalysisResult(BaseModel):
    score: int  # 0-100
    issues: list[StepAnalysisIssue]
    summary: str
```

**Prompt 设计**：

```
你是一位资深测试工程师，请分析以下测试用例步骤的完整性和质量。

用例标题：{title}
分类：{category}
前置条件：{pre_condition}
后置条件：{post_condition}

步骤列表：
{steps_json}

请以严格 JSON 格式返回：
{
  "score": 0-100 的整数,
  "issues": [
    {
      "step_index": 0-based 索引,
      "field": "name|action|expected",
      "severity": "error|warning|suggestion",
      "message": "问题描述",
      "proposed_value": "建议值（可选）"
    }
  ],
  "summary": "整体评价"
}

评审标准：
- error：缺失必填字段（步骤名/操作/预期结果为空）
- warning：步骤描述过短（<10字）、预期不可验证、缺少边界条件
- suggestion：可补充前置数据、可细化操作步骤、可增加异常路径
```

---

### P1 — 高价值 AI 增强

#### 2.3 需求→用例生成（`test_specs` 模块）

**端点**：`POST /api/v1/ai/generate-cases`

**输入**：`requirement_id` 或 `requirement_text` + 生成参数（用例数量、分类偏好）

**输出**：`TestCaseDraft[]`（标题、步骤、预期结果、前置条件、优先级）

**流程**：
1. 从需求文档提取测试点
2. 按测试点生成用例草稿
3. 前端展示草稿列表，用户可编辑后批量保存

#### 2.4 失败根因分析（`failure_analysis` 模块）

**端点**：`POST /api/v1/failure-analysis/analyze`

**输入**：`execution_task_id` + `case_id`

**输出**：根因分类 + 推测原因 + 修复建议 + 关联历史失败

**流程**：
1. 收集执行日志、用例步骤、环境信息
2. AI 分析失败原因（代码缺陷 / 环境问题 / 用例问题 / 数据问题）
3. 关联历史失败记录，识别重复模式

#### 2.5 用例评审建议（`test_specs` 模块）

**端点**：`POST /api/v1/ai/review-case`

**触发**：用例保存时自动触发（异步）或手动触发

**输出**：边界覆盖评估 + 遗漏场景 + 步骤可执行性 + 优先级建议

#### 2.6 智能用例选择（`execution_plan` 模块）

**端点**：`POST /api/v1/ai/recommend-cases`

**输入**：`project_id` + 变更描述/commit range

**输出**：推荐的 `case_id` 列表 + 推荐理由

---

### P2 — AI 原生基础设施

#### 2.7 语义搜索（`search` 模块）

用 embedding 向量做语义搜索，替代纯文本匹配。

**落点**：`search` 模块 + MongoDB Atlas Vector Search 或内存余弦相似度

**流程**：
1. 用例/需求创建时生成 embedding 向量
2. 搜索时将查询词也转为向量
3. 余弦相似度排序 + 关键词匹配融合

#### 2.8 追踪关系分析（`lineage` 模块）

AI 分析需求→用例→执行的追踪链路，自动发现断裂关系。

#### 2.9 项目健康预测（`project` 模块）

AI 基于项目统计数据预测质量风险。

#### 2.10 AI 事件流（Kafka 异步管道）

耗时 AI 操作走 Kafka 异步管道，结果通过 WebSocket 或轮询返回。

---

### 底层 — AI 基础设施

| 组件 | 路径 | 职责 |
|------|------|------|
| AIClient 单例 | `shared/ai/client.py` | 统一 client + 重试 + 超时 + 限流 |
| Prompt 模板管理 | `shared/ai/prompts/` | 版本化 + 热加载 |
| AI 调用审计 | `shared/ai/audit.py` | token 用量 + 耗时 + 结果 |
| AiCallLogDoc | `shared/ai/repository/` | MongoDB 审计日志文档模型 |

---

## 3. 执行计划

| 优先级 | 任务 | 模块 | 预期 commit |
|--------|------|------|------------|
| P0 | 共享 AIClient 封装 | `shared/ai/` | 1 |
| P0 | AI 步骤分析端点 | `system_config/api/ai_routes.py` | 1 |
| P0 | AI 模块测试 | `tests/unit/ai/` | 1 |
| P1 | 需求→用例生成 | `test_specs` + `shared/ai/` | 2-3 |
| P1 | 失败根因分析 | `failure_analysis` + `shared/ai/` | 2 |
| P1 | 用例评审建议 | `test_specs` + `shared/ai/` | 1 |
| P1 | 智能用例选择 | `execution_plan` + `shared/ai/` | 1 |
| P2 | 语义搜索 | `search` + `shared/ai/` | 3 |
| P2 | 追踪关系分析 | `lineage` + `shared/ai/` | 2 |
| P2 | 项目健康预测 | `project` + `shared/ai/` | 2 |
| P2 | AI 事件流 | `shared/kafka/` + `shared/ai/` | 3 |

---

## 4. 架构约束

1. **所有 AI 功能统一走 `AIClient`**，不允许业务模块直接创建 `OpenAI` 实例
2. **Prompt 与代码分离**，P1 起所有 prompt 模板放在 `shared/ai/prompts/` 目录
3. **AI 调用必须记录审计日志**（token 用量、耗时、模型、输入摘要、输出摘要）
4. **配置热加载不变**，继续使用 `ConfigService.get_ai_config()` + MongoDB
5. **异步耗时操作**走 Kafka，不阻塞 API 响应（P2 实现）
6. **测试覆盖**，每个 AI 端点必须有单元测试（mock LLM 响应）

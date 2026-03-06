# 执行进度回传 SDK 设计方案

更新时间：2026-03-03

## 1. 背景与目标

为降低第三方测试框架接入门槛，需要提供官方 SDK，统一完成以下能力：

- 任务状态上报（任务级）
- 测试用例状态上报（用例级）
- 测试步骤结果上报（步骤级）
- 心跳与汇总上报
- 签名鉴权、幂等字段填充、重试与失败缓存

SDK 目标：

1. 第三方服务“最少改动”即可接入。
2. 默认具备生产可用的可靠性（重试、限流、缓冲、幂等）。
3. 与平台回调接口严格对齐，避免多实现分叉。

---

## 2. 设计原则

- 协议优先：SDK 只是协议实现，不承载业务判断。
- 可靠优先：默认“至少一次投递”（At-least-once）。
- 可观测优先：每次上报可追踪（event_id/seq/request_id）。
- 向后兼容：字段新增不破坏旧客户端。
- 多语言可扩展：先提供 Python 参考实现，再按协议生成其他语言 SDK。

---

## 3. 发布形态

## 3.1 首期形态

- `Python SDK`：包名建议 `dml-exec-reporter`
- 版本策略：SemVer（`MAJOR.MINOR.PATCH`）
- 发布渠道：内部 PyPI（或私有源）

## 3.2 后续形态

- `HTTP Sidecar`（可选）：容器化代理，非 Python 框架通过本地 HTTP 调用 sidecar 上报。
- `OpenAPI + Generator`（可选）：生成 Java/Go/Node 客户端。

---

## 4. SDK 能力边界

SDK 负责：

- 构造标准事件 payload
- 计算签名头（HMAC）
- 发送到 `/api/v1/execution/callbacks/progress`
- 失败重试、指数退避、可选本地落盘缓存
- 事件去重辅助（event_id 自动生成）

SDK 不负责：

- 决定测试是否通过（由框架业务逻辑决定）
- 任务编排与调度
- 平台侧状态聚合规则

---

## 5. 对齐平台协议

关联文档：`测试任务下发与进度回传设计方案.md`

目标接口：

- `POST /api/v1/execution/callbacks/progress`

推荐请求头：

- `X-Framework-Id`
- `X-Event-Id`
- `X-Timestamp`
- `X-Signature`

核心事件类型：

- `TASK_STATUS`
- `CASE_STATUS`
- `STEP_RESULT`
- `HEARTBEAT`
- `SUMMARY`

---

## 6. SDK API 设计（Python）

## 6.1 配置对象

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ReporterConfig:
    base_url: str
    framework_id: str
    secret: str
    timeout_sec: float = 3.0
    max_retries: int = 5
    backoff_base_sec: float = 0.3
    backoff_max_sec: float = 10.0
    enable_disk_spool: bool = True
    spool_dir: str = "/tmp/dml-reporter-spool"
    worker_threads: int = 2
    queue_maxsize: int = 5000
```

## 6.2 主客户端

```python
class ExecutionReporter:
    def __init__(self, config: ReporterConfig): ...

    # 任务级
    def report_task_status(
        self,
        task_id: str,
        external_task_id: str | None,
        status: str,
        seq: int,
        detail: dict | None = None,
        event_id: str | None = None,
    ) -> None: ...

    # 用例级
    def report_case_status(
        self,
        task_id: str,
        case_id: str,
        status: str,
        seq: int,
        progress_percent: float | None = None,
        step_total: int | None = None,
        step_passed: int | None = None,
        step_failed: int | None = None,
        step_skipped: int | None = None,
        event_id: str | None = None,
    ) -> None: ...

    # 步骤级
    def report_step_result(
        self,
        task_id: str,
        case_id: str,
        step_id: str,
        status: str,
        seq: int,
        started_at: str | None = None,
        finished_at: str | None = None,
        message: str | None = None,
        artifacts: list[dict] | None = None,
        event_id: str | None = None,
    ) -> None: ...

    # 心跳
    def heartbeat(self, task_id: str, seq: int, event_id: str | None = None) -> None: ...

    # 汇总
    def summary(
        self,
        task_id: str,
        overall_status: str,
        seq: int,
        totals: dict,
        event_id: str | None = None,
    ) -> None: ...

    # 生命周期
    def flush(self, timeout_sec: float | None = None) -> None: ...
    def close(self) -> None: ...
```

## 6.3 异步版本（可选）

- `AsyncExecutionReporter`，基于 `httpx.AsyncClient`
- 方法签名与同步版一致，返回 `await`

## 6.4 详细接口文档

### ReporterConfig 配置类

```python
@dataclass
class ReporterConfig:
    base_url: str                           # 必需：DMLV4 API基础地址
    framework_id: str                       # 必需：框架唯一标识
    secret: str                            # 必需：签名密钥
    timeout_sec: float = 3.0               # 可选：HTTP超时(秒)
    max_retries: int = 5                   # 可选：最大重试次数
    backoff_base_sec: float = 0.3          # 可选：重试退避基准(秒)
    backoff_max_sec: float = 10.0          # 可选：最大退避时间(秒)
    enable_disk_spool: bool = True         # 可选：是否启用落盘缓存
    spool_dir: str = "/tmp/dml-reporter-spool"  # 可选：缓存目录
    worker_threads: int = 2                # 可选：工作线程数
    queue_maxsize: int = 5000              # 可选：队列最大容量
```

### 任务管理接口

#### `get_task(task_id: str) -> ExecutionTask`

**功能**：获取任务详细信息

**参数：**
- `task_id` (str): 任务ID，格式：`ET-YYYY-NNNNNN`

**返回值：**
```python
@dataclass
class ExecutionTask:
    task_id: str                           # 任务ID
    external_task_id: Optional[str]        # 外部任务ID
    framework: str                        # 框架标识
    overall_status: str                   # 总体状态
    case_count: int                       # 用例总数
    reported_case_count: int              # 已上报用例数
    created_at: datetime                  # 创建时间
    stats: TaskStats                      # 统计信息
```

**异常：**
- `TaskNotFoundError`: 任务不存在
- `NetworkError`: 网络请求失败

---

#### `list_tasks(...) -> List[ExecutionTask]`

**功能**：查询任务列表

**参数：**
- `framework` (Optional[str]): 按框架筛选
- `overall_status` (Optional[str]): 按状态筛选
- `limit` (int): 返回数量限制，默认20，最大200
- `offset` (int): 偏移量，默认0

**返回值：** `List[ExecutionTask]`

---

#### `get_task_cases(...) -> List[TaskCase]`

**功能**：获取任务包含的用例列表

**参数：**
- `task_id` (str): 任务ID
- `status` (Optional[str]): 按状态筛选
- `limit` (int): 返回数量限制，默认50，最大500
- `offset` (int): 偏移量

**返回值：**
```python
@dataclass
class TaskCase:
    case_id: str                          # 用例ID
    status: str                          # 用例状态
    progress_percent: Optional[float]     # 进度百分比(0-100)
    step_total: int                      # 步骤总数
    step_passed: int                     # 通过步骤数
    step_failed: int                     # 失败步骤数
    step_skipped: int                    # 跳过步骤数
    started_at: Optional[datetime]       # 开始时间
    finished_at: Optional[datetime]      # 完成时间
```

### 进度上报接口

#### `report_task_status(...) -> None`

**功能**：上报任务级别的执行状态

**参数：**
- `task_id` (str): 任务ID，必需
- `external_task_id` (Optional[str]): 外部任务ID，可选
- `status` (str): 任务状态，必需，值域：`QUEUED|RUNNING|PASSED|FAILED|PARTIAL_FAILED|CANCELLED|TIMEOUT`
- `seq` (int): 事件序列号，必需，同一任务内单调递增
- `detail` (Optional[Dict]): 详细信息，可选
- `event_id` (Optional[str]): 事件ID，可选，为None时自动生成

**异常：**
- `InvalidStatusError`: 无效的状态值
- `ReporterDeliveryError`: 消息投递失败

**示例：**
```python
reporter.report_task_status(
    task_id="ET-2026-000001",
    external_task_id="FW-123",
    status="RUNNING",
    seq=1,
    detail={"started_at": "2026-03-03T10:00:00Z"}
)
```

---

#### `report_case_status(...) -> None`

**功能**：上报单个测试用例的执行状态

**参数：**
- `task_id` (str): 任务ID，必需
- `case_id` (str): 用例ID，必需
- `status` (str): 用例状态，必需，值域：`QUEUED|RUNNING|PASSED|FAILED|SKIPPED|BLOCKED|ERROR`
- `seq` (int): 事件序列号，必需
- `progress_percent` (Optional[float]): 进度百分比，可选，0-100之间
- `step_total` (Optional[int]): 总步骤数，可选，≥0
- `step_passed` (Optional[int]): 通过步骤数，可选，≥0
- `step_failed` (Optional[int]): 失败步骤数，可选，≥0
- `step_skipped` (Optional[int]): 跳过步骤数，可选，≥0
- `event_id` (Optional[str]): 事件ID，可选
- `event_time` (Optional[datetime]): 事件时间，可选

**异常：**
- `InvalidStatusError`: 无效的状态值
- `ReporterDeliveryError`: 消息投递失败

**示例：**
```python
reporter.report_case_status(
    task_id="ET-2026-000001",
    case_id="TC-2026-001",
    status="RUNNING",
    seq=2,
    progress_percent=60.0,
    step_total=10,
    step_passed=6,
    step_failed=0,
    step_skipped=0
)
```

---

#### `report_step_result(...) -> None`

**功能**：上报单个测试步骤的执行结果

**参数：**
- `task_id` (str): 任务ID，必需
- `case_id` (str): 用例ID，必需
- `step_id` (str): 步骤ID，必需
- `status` (str): 步骤状态，必需，值域：`RUNNING|PASSED|FAILED|SKIPPED|ERROR`
- `seq` (int): 事件序列号，必需
- `started_at` (Optional[datetime]): 步骤开始时间，可选
- `finished_at` (Optional[datetime]): 步骤结束时间，可选
- `message` (Optional[str]): 步骤执行消息，可选
- `artifacts` (Optional[List[Dict]]): 附件信息，可选

**附件格式：**
```python
artifacts = [
    {
        "type": "log",                     # 附件类型：log/screenshot/file
        "path": "/path/to/file",           # 文件路径或URL
        "description": "描述信息"           # 可选描述
    }
]
```

**异常：**
- `InvalidStatusError`: 无效的状态值
- `ReporterDeliveryError`: 消息投递失败

**示例：**
```python
reporter.report_step_result(
    task_id="ET-2026-000001",
    case_id="TC-2026-001",
    step_id="step_01",
    status="PASSED",
    seq=3,
    message="电压检查通过",
    artifacts=[
        {"type": "log", "path": "/logs/step_01.log"},
        {"type": "screenshot", "path": "/screenshots/step_01.png"}
    ]
)
```

#### `heartbeat(task_id: str, seq: int, event_id: Optional[str] = None) -> None`

**功能**：发送心跳信号，表示任务仍在执行

**参数：**
- `task_id` (str): 任务ID，必需
- `seq` (int): 事件序列号，必需
- `event_id` (Optional[str]): 事件ID，可选

**示例：**
```python
reporter.heartbeat(task_id="ET-2026-000001", seq=50)
```

#### `summary(task_id: str, overall_status: str, seq: int, totals: Dict, event_id: Optional[str] = None) -> None`

**功能**：发送任务执行汇总信息

**参数：**
- `task_id` (str): 任务ID，必需
- `overall_status` (str): 总体状态，必需
- `seq` (int): 事件序列号，必需
- `totals` (Dict): 汇总数据，必需
- `event_id` (Optional[str]): 事件ID，可选

**汇总数据格式：**
```python
totals = {
    "total_cases": 10,                    # 总用例数
    "passed": 8,                         # 通过用例数
    "failed": 2,                         # 失败用例数
    "skipped": 0,                        # 跳过用例数
    "execution_time": "00:05:30",        # 执行时间
    "coverage": 95.5                     # 自定义指标
}
```

**示例：**
```python
reporter.summary(
    task_id="ET-2026-000001",
    overall_status="PASSED",
    seq=100,
    totals={
        "total_cases": 5,
        "passed": 4,
        "failed": 1,
        "execution_time": "00:15:30"
    }
)
```

### 便捷方法

#### `start_case(task_id, case_id, seq, event_id=None) -> None`

标记用例开始执行，是 `report_case_status` 的便捷包装。

#### `complete_case(task_id, case_id, status, seq, message=None, event_id=None) -> None`

标记用例执行完成。

#### `update_case_progress(task_id, case_id, progress_percent, seq, event_id=None) -> None`

更新用例进度百分比。

### 生命周期管理

#### `flush(timeout_sec=None) -> None`

等待所有待处理的请求发送完成。

**参数：**
- `timeout_sec` (Optional[float]): 超时时间，为None时使用配置的超时时间

#### `close() -> None`

关闭客户端，释放资源。

---

## 7. 事件模型（SDK 内部）

统一事件结构：

```json
{
  "task_id": "ET-2026-000001",
  "external_task_id": "FW-abc-123",
  "event_type": "CASE_STATUS",
  "event_time": "2026-03-03T11:20:00Z",
  "seq": 12,
  "overall_status": "RUNNING",
  "case": {
    "case_id": "TC-2026-001",
    "status": "RUNNING",
    "progress_percent": 60,
    "step_total": 10,
    "step_passed": 6,
    "step_failed": 0,
    "step_skipped": 0
  },
  "meta": {
    "sdk_name": "dml-exec-reporter",
    "sdk_version": "0.1.0",
    "hostname": "runner-01"
  }
}
```

字段约束：

- `seq`：同一任务单调递增（建议由调用方维护）。
- `event_id`：建议 UUIDv7，SDK 可自动生成。
- `event_time`：ISO8601 UTC。

---

## 8. 鉴权与安全

## 8.1 签名算法

- HMAC-SHA256
- 待签名串：`{timestamp}\n{event_id}\n{raw_body}`

请求头规则：

- `X-Timestamp`：Unix 秒
- `X-Event-Id`：事件唯一 ID
- `X-Signature`：`hex(hmac_sha256(secret, signing_string))`

## 8.2 时间窗

- 建议平台默认接受 ±300 秒
- SDK 本地时钟漂移超过阈值时输出警告日志

## 8.3 Secret 管理

- 支持从 env 注入：`DML_REPORTER_SECRET`
- 支持热更新（可选）
- 日志中禁止打印 secret 或完整签名串

---

## 9. 可靠性策略

## 9.1 重试策略

- 对 `5xx` / 网络异常重试
- 对 `4xx`（签名错误/字段错误）不重试，直接失败
- 指数退避 + 抖动：
  - `sleep = min(backoff_max, backoff_base * 2^attempt) + jitter`

## 9.2 缓冲与落盘

- 内存队列：防止业务线程阻塞
- 可选落盘队列（spool）：进程重启后可恢复未发送事件

## 9.3 投递语义

- 默认 At-least-once
- 依赖平台 `event_id` 幂等去重实现“最终仅处理一次”

---

## 10. 错误处理与可观测性

## 10.1 SDK 异常类型

- `ReporterConfigError`
- `ReporterValidationError`
- `ReporterAuthError`
- `ReporterDeliveryError`

## 10.2 指标建议（SDK 侧）

- `reporter_events_total`
- `reporter_events_success_total`
- `reporter_events_retry_total`
- `reporter_events_failed_total`
- `reporter_queue_size`

## 10.3 日志字段

- `task_id`, `case_id`, `event_id`, `event_type`, `seq`, `status_code`, `retry_count`

---

## 11. 接入示例

```python
from dml_exec_reporter import ExecutionReporter, ReporterConfig

cfg = ReporterConfig(
    base_url="https://dml.example.com",
    framework_id="pytest-runner",
    secret="${DML_REPORTER_SECRET}",
)
reporter = ExecutionReporter(cfg)

reporter.report_task_status(
    task_id="ET-2026-000001",
    external_task_id="FW-abc-123",
    status="RUNNING",
    seq=1,
)

reporter.report_case_status(
    task_id="ET-2026-000001",
    case_id="TC-2026-001",
    status="RUNNING",
    seq=2,
    progress_percent=35,
    step_total=20,
    step_passed=7,
)

reporter.report_step_result(
    task_id="ET-2026-000001",
    case_id="TC-2026-001",
    step_id="step-08",
    status="FAILED",
    seq=3,
    message="assert voltage threshold",
)

reporter.summary(
    task_id="ET-2026-000001",
    overall_status="FAILED",
    seq=99,
    totals={"passed": 18, "failed": 2, "skipped": 0},
)

reporter.flush()
reporter.close()
```

---

## 12. 版本兼容与演进

## 12.1 协议版本头

建议增加：
- `X-Protocol-Version: 1`

用于平台渐进升级时平滑兼容。

## 12.2 兼容规则

- 新增可选字段：旧 SDK 可继续工作
- 破坏性变更：提升 MAJOR，并保留迁移窗口

---

## 13. 实施计划

## 13.1 Phase A（MVP）

- Python SDK（同步 API）
- 任务/用例/步骤/心跳/汇总上报
- 签名、重试、幂等字段自动注入

## 13.2 Phase B

- 异步 API
- 落盘缓冲 + 进程恢复
- Prometheus 指标

## 13.3 Phase C

- Sidecar 模式
- 多语言 SDK 生成

---

## 14. 待确认项

1. SDK 首发是否仅 Python？
2. 步骤级结果本期是否强制落库（平台侧）还是仅透传审计？
3. `seq` 由框架维护还是 SDK 自动维护（建议框架维护）？
4. 是否要求企业代理/内网 TLS 双向认证（mTLS）？

---

## 15. 结论

该 SDK 方案可以让第三方测试服务以统一、低门槛方式回传执行进度：

- 对接简单：调用几个标准方法即可。
- 传输可靠：重试 + 幂等 + 缓冲。
- 安全可控：签名验签与时间窗校验。
- 易于扩展：后续可平滑升级为异步/Sidecar/多语言形态。

评审通过后，可按 Phase A 开始实现 SDK 与平台验签联调。

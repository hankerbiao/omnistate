# DMLV4 执行进度回传 SDK

为外部测试框架提供简洁易用的进度回传能力，支持向DMLV4工作流系统上报测试执行进度。

## 特性

- 🔄 **多级别进度上报**：支持任务级、用例级、步骤级进度回传
- 🔒 **安全通信**：HMAC-SHA256签名验证，防篡改和重放攻击
- ⚡ **可靠传输**：支持重试、队列缓冲、事件去重
- 🐍 **Python优先**：同时提供同步和异步API
- 🔌 **易于集成**：专为测试框架设计，最少改动即可接入
- 📊 **实时监控**：支持心跳、汇总等监控功能

## 快速开始

### 安装

```bash
# 开发安装
pip install -e .

# 或者直接使用源码
export PYTHONPATH=$PYTHONPATH:/path/to/dmlv4_execution_sdk
```

### 基础使用

```python
from dmlv4_execution_sdk import ExecutionReporter, ReporterConfig, TaskStatus, CaseStatus

# 1. 配置客户端
config = ReporterConfig(
    base_url="http://your-dmlv4-server/api/v1",
    framework_id="your_framework",
    secret="your_secret_key",
)

# 2. 初始化Reporter
reporter = ExecutionReporter(config)

# 3. 上报进度
task_id = "ET-2026-000001"

# 上报任务开始
reporter.report_task_status(
    task_id=task_id,
    external_task_id="FW-123",
    status=TaskStatus.RUNNING.value,
    seq=1
)

# 上报用例执行
reporter.start_case(task_id, "TESTCASE-001", seq=2)
reporter.update_case_progress(task_id, "TESTCASE-001", 50.0, seq=3)
reporter.complete_case(task_id, "TESTCASE-001", CaseStatus.PASSED.value, seq=4)

# 4. 清理资源
reporter.flush()
reporter.close()
```

### Pytest集成

```python
# conftest.py
import pytest
from dmlv4_execution_sdk import ExecutionReporter, ReporterConfig, DMLV4Plugin

@pytest.fixture(scope="session")
def dmlv4_reporter():
    config = ReporterConfig(
        base_url=os.getenv("DMLV4_BASE_URL"),
        framework_id=os.getenv("DMLV4_FRAMEWORK_ID"),
        secret=os.getenv("DMLV4_SECRET"),
    )
    task_id = os.getenv("DMLV4_TASK_ID")

    plugin = DMLV4Plugin(config, task_id)
    yield plugin
    plugin.close()
```

## API参考

### 核心类

#### `ReporterConfig`
SDK配置类。

```python
@dataclass
class ReporterConfig:
    base_url: str              # DMLV4 API基础地址
    framework_id: str          # 框架唯一标识
    secret: str                # 签名密钥
    timeout_sec: float = 3.0   # 请求超时时间
    max_retries: int = 5       # 最大重试次数
    # ... 其他配置
```

#### `ExecutionReporter`
同步版进度上报客户端。

#### `AsyncExecutionReporter`
异步版进度上报客户端。

### 主要方法

#### 任务管理
- `get_task(task_id)` - 获取任务详情
- `list_tasks()` - 查询任务列表
- `get_task_cases(task_id)` - 获取任务用例列表

#### 进度上报
- `report_task_status()` - 上报任务状态
- `report_case_status()` - 上报用例状态
- `report_step_result()` - 上报步骤结果
- `heartbeat()` - 发送心跳
- `summary()` - 发送汇总

#### 便捷方法
- `start_case()` - 标记用例开始
- `complete_case()` - 标记用例完成
- `update_case_progress()` - 更新用例进度

## 详细API文档

### ReporterConfig 配置类

SDK配置类，用于初始化客户端。

```python
@dataclass
class ReporterConfig:
    base_url: str                           # DMLV4 API基础地址 (必需)
    framework_id: str                       # 框架唯一标识 (必需)
    secret: str                            # 签名密钥 (必需)
    timeout_sec: float = 3.0               # HTTP请求超时时间(秒)
    max_retries: int = 5                   # 最大重试次数
    backoff_base_sec: float = 0.3          # 重试退避基准时间(秒)
    backoff_max_sec: float = 10.0          # 最大退避时间(秒)
    enable_disk_spool: bool = True         # 是否启用落盘缓存
    spool_dir: str = "/tmp/dml-reporter-spool"  # 缓存目录
    worker_threads: int = 2                # 工作线程数
    queue_maxsize: int = 5000              # 队列最大容量
```

**参数说明：**
- `base_url`: DMLV4后端API的基础地址，例如：`"http://localhost:8000/api/v1"`
- `framework_id`: 用于标识外部测试框架的唯一字符串
- `secret`: 用于HMAC签名的密钥字符串

### ExecutionReporter 同步客户端

#### 任务管理API

##### `get_task(task_id: str) -> ExecutionTask`

获取任务详情信息。

**参数：**
- `task_id` (str): 任务ID，例如 `"ET-2026-000001"`

**返回值：**
```python
@dataclass
class ExecutionTask:
    task_id: str                           # 任务ID
    external_task_id: Optional[str]        # 外部任务ID
    framework: str                         # 框架标识
    overall_status: str                    # 总体状态
    case_count: int                        # 用例总数
    reported_case_count: int               # 已上报用例数
    created_at: Optional[datetime]         # 创建时间
    stats: Optional[TaskStats]             # 统计信息
```

**异常：**
- `TaskNotFoundError`: 任务不存在
- `NetworkError`: 网络请求失败

---

##### `list_tasks(framework=None, overall_status=None, limit=20, offset=0) -> List[ExecutionTask]`

查询任务列表。

**参数：**
- `framework` (Optional[str]): 按框架筛选，为None时不过滤
- `overall_status` (Optional[str]): 按状态筛选，例如 `"RUNNING"`
- `limit` (int): 返回数量限制，默认20，最大200
- `offset` (int): 偏移量，用于分页，默认0

**返回值：**
- `List[ExecutionTask]`: 任务列表

---

##### `get_task_cases(task_id, status=None, limit=50, offset=0) -> List[TaskCase]`

获取任务的用例列表。

**参数：**
- `task_id` (str): 任务ID
- `status` (Optional[str]): 按状态筛选，例如 `"RUNNING"`
- `limit` (int): 返回数量限制，默认50，最大500
- `offset` (int): 偏移量，用于分页

**返回值：**
```python
@dataclass
class TaskCase:
    case_id: str                           # 用例ID
    status: str                           # 用例状态
    progress_percent: Optional[float]      # 进度百分比 (0-100)
    step_total: int                        # 步骤总数
    step_passed: int                       # 通过步骤数
    step_failed: int                       # 失败步骤数
    step_skipped: int                      # 跳过步骤数
    started_at: Optional[datetime]         # 开始时间
    finished_at: Optional[datetime]        # 完成时间
```

#### 进度上报API

##### `report_task_status(task_id, external_task_id, status, seq, detail=None, event_id=None, event_time=None) -> None`

上报任务级别的执行状态。

**参数：**
- `task_id` (str): 任务ID，必需
- `external_task_id` (Optional[str]): 外部任务ID，可选
- `status` (str): 任务状态，必需，必须是TaskStatus枚举值之一
- `seq` (int): 事件序列号，必需，同一任务内必须单调递增
- `detail` (Optional[Dict[str, Any]]): 详细信息字典，可选
- `event_id` (Optional[str]): 事件ID，可选，为None时自动生成
- `event_time` (Optional[datetime]): 事件时间，可选，为None时使用当前时间

**异常：**
- `InvalidStatusError`: 无效的状态值
- `ReporterDeliveryError`: 消息投递失败

**示例：**
```python
reporter.report_task_status(
    task_id="ET-2026-000001",
    external_task_id="FW-123",
    status=TaskStatus.RUNNING.value,
    seq=1,
    detail={"started_at": datetime.now().isoformat()}
)
```

---

##### `report_case_status(task_id, case_id, status, seq, progress_percent=None, step_total=None, step_passed=None, step_failed=None, step_skipped=None, event_id=None, event_time=None) -> None`

上报单个测试用例的执行状态。

**参数：**
- `task_id` (str): 任务ID，必需
- `case_id` (str): 用例ID，必需
- `status` (str): 用例状态，必需，必须是CaseStatus枚举值之一
- `seq` (int): 事件序列号，必需
- `progress_percent` (Optional[float]): 进度百分比，0-100之间的浮点数
- `step_total` (Optional[int]): 总步骤数，大于等于0的整数
- `step_passed` (Optional[int]): 通过步骤数，大于等于0的整数
- `step_failed` (Optional[int]): 失败步骤数，大于等于0的整数
- `step_skipped` (Optional[int]): 跳过步骤数，大于等于0的整数
- `event_id` (Optional[str]): 事件ID，可选
- `event_time` (Optional[datetime]): 事件时间，可选

**异常：**
- `InvalidStatusError`: 无效的状态值
- `ReporterDeliveryError`: 消息投递失败

**示例：**
```python
reporter.report_case_status(
    task_id="ET-2026-000001",
    case_id="TESTCASE-001",
    status=CaseStatus.RUNNING.value,
    seq=2,
    progress_percent=50.0,
    step_total=10,
    step_passed=5,
    step_failed=0,
    step_skipped=0
)
```

---

##### `report_step_result(task_id, case_id, step_id, status, seq, started_at=None, finished_at=None, message=None, artifacts=None, event_id=None, event_time=None) -> None`

上报单个测试步骤的执行结果。

**参数：**
- `task_id` (str): 任务ID，必需
- `case_id` (str): 用例ID，必需
- `step_id` (str): 步骤ID，必需
- `status` (str): 步骤状态，必需，必须是StepStatus枚举值之一
- `seq` (int): 事件序列号，必需
- `started_at` (Optional[datetime]): 步骤开始时间，可选
- `finished_at` (Optional[datetime]): 步骤结束时间，可选
- `message` (Optional[str]): 步骤执行消息，可选
- `artifacts` (Optional[List[Dict[str, Any]]]): 附件信息列表，可选
- `event_id` (Optional[str]): 事件ID，可选
- `event_time` (Optional[datetime]): 事件时间，可选

**附件格式：**
```python
artifacts = [
    {
        "type": "log",                       # 附件类型: log/screenshot/file
        "path": "/path/to/file",             # 文件路径或URL
        "description": "日志文件描述"          # 可选描述
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
    case_id="TESTCASE-001",
    step_id="step_01",
    status=StepStatus.PASSED.value,
    seq=3,
    started_at=datetime.now(),
    finished_at=datetime.now(),
    message="电压检查通过",
    artifacts=[
        {"type": "log", "path": "/logs/step_01.log"},
        {"type": "screenshot", "path": "/screenshots/step_01.png"}
    ]
)
```

---

##### `heartbeat(task_id: str, seq: int, event_id: Optional[str] = None) -> None`

发送心跳信号，表示任务仍在执行中。

**参数：**
- `task_id` (str): 任务ID，必需
- `seq` (int): 事件序列号，必需
- `event_id` (Optional[str]): 事件ID，可选

**示例：**
```python
reporter.heartbeat(task_id="ET-2026-000001", seq=99)
```

---

##### `summary(task_id, overall_status, seq, totals, event_id=None) -> None`

发送任务执行汇总信息。

**参数：**
- `task_id` (str): 任务ID，必需
- `overall_status` (str): 总体状态，必需
- `seq` (int): 事件序列号，必需
- `totals` (Dict[str, Any]): 汇总数据字典，必需
- `event_id` (Optional[str]): 事件ID，可选

**汇总数据格式：**
```python
totals = {
    "total_cases": 10,                      # 总用例数
    "passed": 8,                           # 通过用例数
    "failed": 2,                           # 失败用例数
    "skipped": 0,                          # 跳过用例数
    "execution_time": "00:05:30",          # 执行时间
    "coverage": 95.5                       # 覆盖率等自定义指标
}
```

**示例：**
```python
reporter.summary(
    task_id="ET-2026-000001",
    overall_status=TaskStatus.PASSED.value,
    seq=100,
    totals={
        "total_cases": 1,
        "passed": 1,
        "failed": 0,
        "execution_time": "00:01:30"
    }
)
```

#### 便捷方法

##### `start_case(task_id, case_id, seq, event_id=None) -> None`

标记测试用例开始执行，是 `report_case_status` 的便捷包装。

**参数：**
- `task_id` (str): 任务ID
- `case_id` (str): 用例ID
- `seq` (int): 序列号
- `event_id` (Optional[str]): 事件ID

---

##### `complete_case(task_id, case_id, status, seq, message=None, event_id=None) -> None`

标记测试用例执行完成。

**参数：**
- `task_id` (str): 任务ID
- `case_id` (str): 用例ID
- `status` (str): 执行状态
- `seq` (int): 序列号
- `message` (Optional[str]): 完成消息
- `event_id` (Optional[str]): 事件ID

---

##### `update_case_progress(task_id, case_id, progress_percent, seq, event_id=None) -> None`

更新测试用例的执行进度百分比。

**参数：**
- `task_id` (str): 任务ID
- `case_id` (str): 用例ID
- `progress_percent` (float): 进度百分比 (0-100)
- `seq` (int): 序列号
- `event_id` (Optional[str]): 事件ID

#### 生命周期管理

##### `flush(timeout_sec=None) -> None`

等待所有待处理的请求发送完成。

**参数：**
- `timeout_sec` (Optional[float]): 等待超时时间，为None时使用配置的timeout

---

##### `close() -> None`

关闭客户端，释放资源。

### AsyncExecutionReporter 异步客户端

异步版本的客户端提供与同步版本相同的API，只是方法都为async方法。

**主要差异：**
- 所有方法都是异步的，使用 `async def` 定义
- 需要使用 `await` 调用
- 更好的并发性能

**示例：**
```python
async def async_example():
    config = ReporterConfig(...)
    async_reporter = AsyncExecutionReporter(config)

    await async_reporter.report_task_status(
        task_id="ET-2026-000001",
        external_task_id="FW-123",
        status=TaskStatus.RUNNING.value,
        seq=1
    )

    await async_reporter.close()
```

### 状态枚举

#### 任务状态
```python
class TaskStatus(Enum):
    QUEUED = "QUEUED"          # 排队等待
    RUNNING = "RUNNING"        # 正在执行
    PASSED = "PASSED"          # 全部通过
    FAILED = "FAILED"          # 存在失败
    PARTIAL_FAILED = "PARTIAL_FAILED"  # 部分失败
    CANCELLED = "CANCELLED"    # 已取消
    TIMEOUT = "TIMEOUT"        # 执行超时
```

#### 用例状态
```python
class CaseStatus(Enum):
    QUEUED = "QUEUED"          # 排队等待
    RUNNING = "RUNNING"        # 正在执行
    PASSED = "PASSED"          # 用例通过
    FAILED = "FAILED"          # 用例失败
    SKIPPED = "SKIPPED"        # 用例跳过
    BLOCKED = "BLOCKED"        # 用例阻塞
    ERROR = "ERROR"            # 用例错误
```

#### 步骤状态
```python
class StepStatus(Enum):
    RUNNING = "RUNNING"        # 步骤执行中
    PASSED = "PASSED"          # 步骤通过
    FAILED = "FAILED"          # 步骤失败
    SKIPPED = "SKIPPED"        # 步骤跳过
    ERROR = "ERROR"            # 步骤错误
```

## 安全机制

SDK使用HMAC-SHA256签名确保通信安全：

```
signature = HMAC-SHA256(
    secret,
    f"{timestamp}\n{event_id}\n{request_body}"
).hexdigest()
```

请求必须包含以下HTTP头：
- `X-Framework-Id`: 框架标识
- `X-Event-Id`: 事件唯一ID
- `X-Timestamp`: Unix时间戳
- `X-Signature`: HMAC签名

## 错误处理

SDK定义了以下异常类型：

- `DMLV4SDKError` - 基础异常
- `ReporterConfigError` - 配置错误
- `ReporterValidationError` - 数据校验失败
- `ReporterAuthError` - 认证失败
- `ReporterDeliveryError` - 消息投递失败
- `TaskNotFoundError` - 任务不存在
- `InvalidStatusError` - 无效状态值
- `SignatureError` - 签名验证失败
- `NetworkError` - 网络请求失败

## 配置说明

### 环境变量

```bash
# 必需配置
export DMLV4_SECRET="your-secret-key"
export DMLV4_TASK_ID="ET-2026-000001"

# 可选配置
export DMLV4_BASE_URL="http://localhost:8000/api/v1"
export DMLV4_FRAMEWORK_ID="your-framework"
```

### 可靠性配置

```python
config = ReporterConfig(
    # 基础配置
    base_url="http://localhost:8000/api/v1",
    framework_id="my_framework",
    secret="my_secret",

    # 可靠性配置
    timeout_sec=30.0,          # 请求超时
    max_retries=5,             # 最大重试次数
    backoff_base_sec=0.3,      # 重试退避基准
    backoff_max_sec=10.0,      # 最大退避时间

    # 缓冲配置
    enable_disk_spool=True,    # 启用落盘缓存
    spool_dir="/tmp/spool",    # 缓存目录
    queue_maxsize=5000,        # 队列最大容量
)
```

## 命令行工具

SDK提供了 `dmlv4-reporter` 命令行工具，方便在命令行中直接测试和上报进度。

### 安装CLI工具

```bash
# 从源码安装（会安装命令行工具）
pip install -e .

# 或者使用setup.py
python setup.py install
```

### 全局参数

所有命令都支持以下全局参数：

```bash
--base-url URL        # DMLV4 API基础地址 (可使用DMLV4_BASE_URL环境变量)
--framework-id ID     # 框架标识 (可使用DMLV4_FRAMEWORK_ID环境变量)
--secret KEY          # 签名密钥 (可使用DMLV4_SECRET环境变量)
--timeout SECONDS     # 请求超时时间，默认30秒
--retries COUNT       # 最大重试次数，默认3次
--version             # 显示版本信息
```

### 命令参考

#### 1. task-status - 上报任务状态

```bash
dmlv4-reporter task-status [选项]
```

**参数：**
- `--task-id TEXT` (必需): 任务ID，例如 `ET-2026-000001`
- `--external-id TEXT` (可选): 外部任务ID
- `--status TEXT` (必需): 任务状态，值必须为：
  - `QUEUED` - 排队等待
  - `RUNNING` - 正在执行
  - `PASSED` - 全部通过
  - `FAILED` - 存在失败
  - `PARTIAL_FAILED` - 部分失败
  - `CANCELLED` - 已取消
  - `TIMEOUT` - 执行超时
- `--seq INTEGER` (必需): 事件序列号，必须单调递增
- `--detail JSON` (可选): 详细信息，JSON格式

**示例：**
```bash
# 上报任务开始执行
dmlv4-reporter task-status \
  --task-id ET-2026-000001 \
  --external-id FW-123 \
  --status RUNNING \
  --seq 1 \
  --detail '{"started_at": "2026-03-03T10:00:00Z"}'

# 上报任务完成
dmlv4-reporter task-status \
  --task-id ET-2026-000001 \
  --status PASSED \
  --seq 99 \
  --detail '{"finished_at": "2026-03-03T10:30:00Z", "duration": "00:30:00"}'
```

#### 2. case-status - 上报用例状态

```bash
dmlv4-reporter case-status [选项]
```

**参数：**
- `--task-id TEXT` (必需): 任务ID
- `--case-id TEXT` (必需): 用例ID
- `--status TEXT` (必需): 用例状态，值必须为：
  - `QUEUED` - 排队等待
  - `RUNNING` - 正在执行
  - `PASSED` - 用例通过
  - `FAILED` - 用例失败
  - `SKIPPED` - 用例跳过
  - `BLOCKED` - 用例阻塞
  - `ERROR` - 用例错误
- `--seq INTEGER` (必需): 事件序列号
- `--progress FLOAT` (可选): 进度百分比，0-100之间
- `--step-total INTEGER` (可选): 总步骤数
- `--step-passed INTEGER` (可选): 通过步骤数
- `--step-failed INTEGER` (可选): 失败步骤数
- `--step-skipped INTEGER` (可选): 跳过步骤数

**示例：**
```bash
# 上报用例开始执行
dmlv4-reporter case-status \
  --task-id ET-2026-000001 \
  --case-id TESTCASE-001 \
  --status RUNNING \
  --seq 2

# 上报用例执行进度
dmlv4-reporter case-status \
  --task-id ET-2026-000001 \
  --case-id TESTCASE-001 \
  --status RUNNING \
  --seq 3 \
  --progress 50.0 \
  --step-total 10 \
  --step-passed 5

# 上报用例执行完成
dmlv4-reporter case-status \
  --task-id ET-2026-000001 \
  --case-id TESTCASE-001 \
  --status PASSED \
  --seq 4 \
  --step-total 10 \
  --step-passed 10
```

#### 3. step-result - 上报步骤结果

```bash
dmlv4-reporter step-result [选项]
```

**参数：**
- `--task-id TEXT` (必需): 任务ID
- `--case-id TEXT` (必需): 用例ID
- `--step-id TEXT` (必需): 步骤ID
- `--status TEXT` (必需): 步骤状态，值必须为：
  - `RUNNING` - 步骤执行中
  - `PASSED` - 步骤通过
  - `FAILED` - 步骤失败
  - `SKIPPED` - 步骤跳过
  - `ERROR` - 步骤错误
- `--seq INTEGER` (必需): 事件序列号
- `--started-at DATETIME` (可选): 开始时间，ISO格式
- `--finished-at DATETIME` (可选): 结束时间，ISO格式
- `--message TEXT` (可选): 步骤消息
- `--artifacts JSON` (可选): 附件信息，JSON格式

**附件JSON格式：**
```json
[
  {
    "type": "log",
    "path": "/path/to/logfile.log",
    "description": "日志文件描述"
  },
  {
    "type": "screenshot",
    "path": "/path/to/screenshot.png",
    "description": "截图文件"
  }
]
```

**示例：**
```bash
# 上报步骤执行完成
dmlv4-reporter step-result \
  --task-id ET-2026-000001 \
  --case-id TESTCASE-001 \
  --step-id step_01 \
  --status PASSED \
  --seq 5 \
  --started-at "2026-03-03T10:05:00Z" \
  --finished-at "2026-03-03T10:06:30Z" \
  --message "电压检查通过"

# 上报步骤失败，包含附件
dmlv4-reporter step-result \
  --task-id ET-2026-000001 \
  --case-id TESTCASE-001 \
  --step-id step_02 \
  --status FAILED \
  --seq 6 \
  --finished-at "2026-03-03T10:10:00Z" \
  --message "电流阈值检查失败" \
  --artifacts '[{"type": "log", "path": "/logs/step_02.log"}]'
```

#### 4. heartbeat - 发送心跳

```bash
dmlv4-reporter heartbeat [选项]
```

**参数：**
- `--task-id TEXT` (必需): 任务ID
- `--seq INTEGER` (必需): 事件序列号

**示例：**
```bash
# 发送心跳
dmlv4-reporter heartbeat \
  --task-id ET-2026-000001 \
  --seq 50
```

#### 5. summary - 发送汇总

```bash
dmlv4-reporter summary [选项]
```

**参数：**
- `--task-id TEXT` (必需): 任务ID
- `--status TEXT` (必需): 总体状态
- `--seq INTEGER` (必需): 事件序列号
- `--totals JSON` (可选): 汇总数据，JSON格式

**示例：**
```bash
# 发送任务汇总
dmlv4-reporter summary \
  --task-id ET-2026-000001 \
  --status PASSED \
  --seq 100 \
  --totals '{"total_cases": 5, "passed": 4, "failed": 1, "execution_time": "00:15:30"}'
```

#### 6. demo - 运行演示

```bash
dmlv4-reporter demo --task-id TASK_ID
```

运行一个完整的演示，展示SDK的各种功能。

**参数：**
- `--task-id TEXT` (必需): 任务ID，用于演示

**示例：**
```bash
# 运行完整演示
dmlv4-reporter demo --task-id ET-2026-000001
```

### 环境变量配置

建议使用环境变量来配置常用参数：

```bash
# 设置环境变量
export DMLV4_BASE_URL="http://localhost:8000/api/v1"
export DMLV4_FRAMEWORK_ID="cli-tool"
export DMLV4_SECRET="your-secret-key"

# 简化命令调用
dmlv4-reporter task-status --task-id ET-2026-000001 --status RUNNING --seq 1
```

### 错误处理

CLI工具的退出码约定：
- `0`: 成功
- `1`: 一般错误（配置错误、网络错误等）
- `2`: 参数错误

错误信息会输出到stderr，格式为：
```
❌ 错误描述
```

### 返回值

CLI工具执行成功时会在stdout输出成功信息：
```
✅ 任务状态已上报: ET-2026-000001 -> RUNNING
```

执行失败时会输出错误信息并返回非零退出码。

## 最佳实践

### 1. 序列号管理
为每个任务维护单调递增的序列号：

```python
# 使用外部序列号管理
seq = get_external_seq()
reporter.report_case_status(task_id, case_id, status, seq)

# 或让SDK自动生成事件ID，序列号由框架管理
event_id = None  # 让SDK生成
seq = framework.get_next_seq()
```

### 2. 错误处理
```python
try:
    reporter.report_task_status(task_id, None, status, seq)
except ReporterAuthError:
    # 认证错误，通常是密钥问题
    logger.error("认证失败，请检查密钥配置")
except ReporterDeliveryError:
    # 投递失败，可能需要重试或落盘
    logger.warning("进度上报失败，将重试")
except NetworkError:
    # 网络错误，可能是服务不可用
    logger.error("网络连接失败")
```

### 3. 资源清理
```python
try:
    # 业务逻辑
    reporter.report_progress(...)
finally:
    # 总是清理资源
    reporter.flush()    # 等待发送完成
    reporter.close()    # 关闭连接
```

### 4. 性能优化
- 使用批量上报减少HTTP请求
- 异步版本适合高并发场景
- 启用落盘缓存防止数据丢失
- 合理设置队列大小和重试策略

## 示例

完整示例请参考：
- [基础使用示例](examples/basic_usage.py)
- [Pytest集成示例](examples/pytest_integration.py)

## 开发和测试

```bash
# 运行基础示例
python examples/basic_usage.py

# 运行pytest集成示例
DMLV4_SECRET=your_secret \
DMLV4_TASK_ID=ET-2026-000001 \
python -m pytest examples/pytest_integration.py -v
```

## 许可证

本项目采用与DMLV4项目相同的许可证。

## 贡献

欢迎提交Issue和Pull Request来改进这个SDK。

## 更新日志

### v0.1.0
- 初始版本
- 支持任务/用例/步骤进度上报
- 集成pytest插件
- 同步和异步API
- 完整的错误处理和重试机制
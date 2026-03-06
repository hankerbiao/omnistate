"""
DMLV4 执行进度回传 SDK

为外部测试框架提供简洁易用的进度回传能力，支持：
- 任务状态上报
- 测试用例状态上报
- 测试步骤结果上报
- 签名鉴权和可靠传输
"""

from .client import ExecutionReporter, AsyncExecutionReporter
from .models import (
    ReporterConfig,
    TaskStats,
    ExecutionTask,
    TaskCase,
    CaseProgress,
    StepProgress,
    ProgressCallback,
)
from .exceptions import (
    DMLV4SDKError,
    ReporterConfigError,
    ReporterValidationError,
    ReporterAuthError,
    ReporterDeliveryError,
)

__version__ = "0.1.0"
__all__ = [
    "ExecutionReporter",
    "AsyncExecutionReporter",
    "ReporterConfig",
    "TaskStats",
    "ExecutionTask",
    "TaskCase",
    "CaseProgress",
    "StepProgress",
    "ProgressCallback",
    "DMLV4SDKError",
    "ReporterConfigError",
    "ReporterValidationError",
    "ReporterAuthError",
    "ReporterDeliveryError",
]
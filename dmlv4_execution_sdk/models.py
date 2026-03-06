"""SDK 数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class CaseStatus(Enum):
    """用例状态枚举"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class StepStatus(Enum):
    """步骤状态枚举"""
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class EventType(Enum):
    """事件类型枚举"""
    TASK_STATUS = "TASK_STATUS"
    CASE_STATUS = "CASE_STATUS"
    STEP_RESULT = "STEP_RESULT"
    HEARTBEAT = "HEARTBEAT"
    SUMMARY = "SUMMARY"


@dataclass
class ReporterConfig:
    """SDK 配置对象"""
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


@dataclass
class TaskStats:
    """任务统计信息"""
    queued: int = 0
    running: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    blocked: int = 0
    error: int = 0


@dataclass
class ExecutionTask:
    """执行任务信息"""
    task_id: str
    external_task_id: Optional[str] = None
    framework: str = ""
    overall_status: str = ""
    case_count: int = 0
    reported_case_count: int = 0
    created_at: Optional[datetime] = None
    stats: Optional[TaskStats] = None


@dataclass
class TaskCase:
    """任务用例信息"""
    case_id: str
    status: str = ""
    progress_percent: Optional[float] = None
    step_total: int = 0
    step_passed: int = 0
    step_failed: int = 0
    step_skipped: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@dataclass
class CaseProgress:
    """用例进度信息"""
    case_id: str
    status: Optional[str] = None
    progress_percent: Optional[float] = None
    step_total: Optional[int] = None
    step_passed: Optional[int] = None
    step_failed: Optional[int] = None
    step_skipped: Optional[int] = None


@dataclass
class StepProgress:
    """步骤进度信息"""
    case_id: str
    step_id: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    message: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProgressCallback:
    """进度回调请求"""
    task_id: str
    external_task_id: Optional[str] = None
    event_type: str
    seq: int
    event_time: Optional[datetime] = None
    overall_status: Optional[str] = None
    case: Optional[CaseProgress] = None
    step: Optional[StepProgress] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "task_id": self.task_id,
            "external_task_id": self.external_task_id,
            "event_type": self.event_type,
            "seq": self.seq,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "overall_status": self.overall_status,
            "summary": self.summary,
            "meta": self.meta,
        }

        if self.case:
            result["case"] = {
                "case_id": self.case.case_id,
                "status": self.case.status,
                "progress_percent": self.case.progress_percent,
                "step_total": self.case.step_total,
                "step_passed": self.case.step_passed,
                "step_failed": self.case.step_failed,
                "step_skipped": self.case.step_skipped,
            }

        if self.step:
            result["step"] = {
                "case_id": self.step.case_id,
                "step_id": self.step.step_id,
                "status": self.step.status,
                "started_at": self.step.started_at.isoformat() if self.step.started_at else None,
                "finished_at": self.step.finished_at.isoformat() if self.step.finished_at else None,
                "message": self.step.message,
                "artifacts": self.step.artifacts,
            }

        return result
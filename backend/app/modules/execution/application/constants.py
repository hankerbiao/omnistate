"""执行模块状态常量与枚举。"""

from enum import Enum


class ScheduleStatus(str, Enum):
    """调度状态：描述是否已到触发阶段。"""
    READY = "READY"
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"


class DispatchStatus(str, Enum):
    """下发状态。"""
    PENDING = "PENDING"
    DISPATCHING = "DISPATCHING"
    DISPATCHED = "DISPATCHED"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    COMPLETED = "COMPLETED"


class ConsumeStatus(str, Enum):
    """消费状态。"""
    PENDING = "PENDING"
    CONSUMED = "CONSUMED"


class OverallStatus(str, Enum):
    """总体执行状态。"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class CaseStatus(str, Enum):
    """用例执行状态。"""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AgentStatus(str, Enum):
    """代理状态。"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"
    HEARTBEAT_LOST = "HEARTBEAT_LOST"


FINAL_CASE_STATUSES = {CaseStatus.PASSED, CaseStatus.FAILED, CaseStatus.SKIPPED}
FINAL_TASK_STATUSES = {OverallStatus.PASSED, OverallStatus.FAILED, OverallStatus.SKIPPED, OverallStatus.CANCELLED}

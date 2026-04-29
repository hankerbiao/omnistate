"""测试执行模型导出。"""
from .execution import (
    ExecutionAgentDoc,
    ExecutionTaskDoc,
    ExecutionTaskCaseDoc,
)
from .execution_event import ExecutionEventDoc


__all__ = [
    "ExecutionTaskDoc",
    "ExecutionTaskCaseDoc",
    "ExecutionAgentDoc",
    "ExecutionEventDoc",
    "DOCUMENT_MODELS",
]

DOCUMENT_MODELS = [
    ExecutionAgentDoc,
    ExecutionEventDoc,
    ExecutionTaskDoc,
    ExecutionTaskCaseDoc,
]

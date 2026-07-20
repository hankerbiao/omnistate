"""测试执行模型导出。"""
from .execution import (
    ExecutionAgentDoc,
    ExecutionTaskDoc,
    ExecutionTaskCaseDoc,
)
from .execution_biz_log import ExecutionBizLogDoc


__all__ = [
    "ExecutionTaskDoc",
    "ExecutionTaskCaseDoc",
    "ExecutionAgentDoc",
    "ExecutionBizLogDoc",
    "DOCUMENT_MODELS",
]

DOCUMENT_MODELS = [
    ExecutionAgentDoc,
    ExecutionBizLogDoc,
    ExecutionTaskDoc,
    ExecutionTaskCaseDoc,
]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)

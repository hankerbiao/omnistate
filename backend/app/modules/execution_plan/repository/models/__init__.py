from app.modules.execution_plan.repository.models.execution_plan import (
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
    ManualExecutionResultDoc,
)
from app.modules.execution_plan.repository.models.change_log import (
    ExecutionPlanChangeLogDoc,
)

DOCUMENT_MODELS = [
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
    ManualExecutionResultDoc,
    ExecutionPlanChangeLogDoc,
]

__all__ = [
    "ExecutionPlanDoc",
    "ExecutionPlanItemDoc",
    "ManualExecutionResultDoc",
    "ExecutionPlanChangeLogDoc",
    "DOCUMENT_MODELS",
]

from app.shared.infrastructure.document_registry import register_document_model

for _model in DOCUMENT_MODELS:
    register_document_model(_model)

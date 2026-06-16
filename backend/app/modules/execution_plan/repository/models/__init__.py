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

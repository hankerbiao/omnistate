from app.modules.execution_plan.repository.models.execution_plan import (
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
    ManualExecutionResultDoc,
)

DOCUMENT_MODELS = [
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
    ManualExecutionResultDoc,
]

__all__ = [
    "ExecutionPlanDoc",
    "ExecutionPlanItemDoc",
    "ManualExecutionResultDoc",
    "DOCUMENT_MODELS",
]

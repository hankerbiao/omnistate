"""Execution plan API route composition."""

from fastapi import APIRouter

from app.modules.execution_plan.api._route_support import _resolve_assignee_id
from app.modules.execution_plan.api.routes_archive import router as archive_router
from app.modules.execution_plan.api.routes_dispatch import router as dispatch_router
from app.modules.execution_plan.api.routes_items import router as items_router
from app.modules.execution_plan.api.routes_plans import router as plans_router
from app.modules.execution_plan.api.routes_results import router as results_router

router = APIRouter(prefix="/execution-plans", tags=["ExecutionPlan"])

# Static item routes must be registered before /items/{item_id}.
router.include_router(archive_router)
router.include_router(dispatch_router)
router.include_router(results_router)
router.include_router(plans_router)
router.include_router(items_router)

__all__ = ["router", "_resolve_assignee_id"]

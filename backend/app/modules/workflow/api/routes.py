from fastapi import APIRouter

from app.modules.workflow.api.routes_catalog import router as catalog_router
from app.modules.workflow.api.routes_items import router as items_router
from app.modules.workflow.api.routes_relations import router as relations_router
from app.modules.workflow.api.routes_transitions import router as transitions_router

router = APIRouter(prefix="/work-items", tags=["WorkItems"])
router.include_router(catalog_router)
router.include_router(items_router)
router.include_router(relations_router)
router.include_router(transitions_router)

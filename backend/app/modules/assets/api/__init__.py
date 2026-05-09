from fastapi import APIRouter

from .routes_duts import router as duts_router

router = APIRouter(prefix="/assets", tags=["Assets"])
router.include_router(duts_router)

__all__ = ["router"]
from fastapi import APIRouter

from app.modules.auth.api.routes_login import router as login_router
from app.modules.auth.api.routes_navigation import router as navigation_router
from app.modules.auth.api.routes_permissions import router as permissions_router
from app.modules.auth.api.routes_roles import router as roles_router
from app.modules.auth.api.routes_users import router as users_router

router = APIRouter(prefix="/auth", tags=["Auth"])
router.include_router(login_router)
router.include_router(users_router)
router.include_router(navigation_router)
router.include_router(roles_router)
router.include_router(permissions_router)

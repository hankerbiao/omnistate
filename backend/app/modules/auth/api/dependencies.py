from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from app.modules.auth.service import RbacService
from app.shared.auth import get_current_user


def get_rbac_service() -> RbacService:
    return RbacService()


RbacServiceDep = Annotated[RbacService, Depends(get_rbac_service)]


def is_admin_user(current_user: dict) -> bool:
    role_ids = current_user.get("role_ids", [])
    return any("ADMIN" in str(role_id).upper() for role_id in role_ids)


async def require_admin_user(current_user=Depends(get_current_user)):
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="admin only")
    return current_user

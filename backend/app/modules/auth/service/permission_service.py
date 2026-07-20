"""Static permission read service."""

from __future__ import annotations

from typing import Any, Dict, List

from app.modules.auth.permissions import list_permissions


class PermissionService:
    """Expose the code-defined permission registry."""

    async def list_permissions(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        permissions = list_permissions()
        return permissions[offset : offset + limit]

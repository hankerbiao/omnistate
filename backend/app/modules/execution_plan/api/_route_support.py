"""Shared dependencies and identity helpers for execution plan routes."""

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status

from app.shared.auth import is_admin_role, require_permission

READ_DEP = [Depends(require_permission("execution_tasks:read"))]
WRITE_DEP = [Depends(require_permission("execution_tasks:write"))]


def get_user_id(current_user: Dict[str, Any]) -> str:
    """Extract the stable user identifier from the auth payload."""
    return current_user.get("user_id") or current_user.get("id") or ""


def _resolve_assignee_id(current_user: Dict[str, Any], assignee_id: Optional[str]) -> str:
    """Allow administrators to query another assignee; others can only query themselves."""
    current_user_id = get_user_id(current_user)
    if not assignee_id or assignee_id == current_user_id:
        return current_user_id
    if is_admin_role(current_user.get("role_ids", [])):
        return assignee_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能查询自己的计划任务")

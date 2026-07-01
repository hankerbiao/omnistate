"""执行计划用户查询适配器。

由 auth 模块提供实现，适配到 execution_plan 的 UserQueryPort。
"""
from __future__ import annotations

from app.modules.execution_plan.application.ports import UserQueryPort


class PlanUserQueryAdapter(UserQueryPort):
    """适配 UserDoc 到 UserQueryPort。

    消除 execution_plan 对 auth.repository.models 的直接依赖。
    """

    async def is_admin(self, user_id: str) -> bool:
        from app.modules.auth.repository.models import UserDoc
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            return False
        return any(
            rid.strip().upper().replace("ROLE_", "") == "ADMIN"
            for rid in (user.role_ids or [])
        )

"""定时执行任务的调度持久化边界。"""

from __future__ import annotations

from datetime import datetime, timedelta

from beanie import UpdateResponse

from app.modules.execution.repository.models import ExecutionTaskDoc

SCHEDULED = "SCHEDULED"
PENDING = "PENDING"
READY = "READY"


class ExecutionTaskScheduleRepository:
    """封装定时任务扫描、原子 claim 与过期租约回收。"""

    @staticmethod
    def _due_filter(now: datetime) -> dict:
        return {
            "schedule_type": SCHEDULED,
            "schedule_status": PENDING,
            "planned_at": {"$lte": now},
            "is_deleted": False,
        }

    async def list_due_tasks(self, now: datetime, limit: int) -> list[ExecutionTaskDoc]:
        """按计划时间返回本轮候选任务。"""
        return await (
            ExecutionTaskDoc.find(self._due_filter(now))
            .sort("planned_at")
            .limit(limit)
            .to_list()
        )

    async def claim_due_task(
        self,
        task_id: str,
        *,
        now: datetime,
        owner: str,
        lease_seconds: int,
    ) -> ExecutionTaskDoc | None:
        """原子 claim 一条仍满足到期条件的 PENDING 任务。"""
        query = {"task_id": task_id, **self._due_filter(now)}
        return await ExecutionTaskDoc.find_one(query).update(
            {"$set": {
                "schedule_status": READY,
                "claim_owner": owner,
                "lease_until": now + timedelta(seconds=lease_seconds),
                "last_claimed_at": now,
            }},
            response_type=UpdateResponse.NEW_DOCUMENT,
        )

    async def recover_expired_leases(self, now: datetime, limit: int) -> int:
        """批量回收有界数量的过期 READY 任务并重置为 PENDING。"""
        expired_filter = {
            "schedule_type": SCHEDULED,
            "schedule_status": READY,
            "lease_until": {"$lt": now},
            "is_deleted": False,
        }
        docs = await ExecutionTaskDoc.find(expired_filter).limit(limit).to_list()
        ids = [doc.id for doc in docs if doc.id is not None]
        if not ids:
            return 0

        result = await ExecutionTaskDoc.get_pymongo_collection().update_many(
            {"_id": {"$in": ids}, **expired_filter},
            {"$set": {
                "schedule_status": PENDING,
                "claim_owner": None,
                "lease_until": None,
            }},
        )
        return result.modified_count

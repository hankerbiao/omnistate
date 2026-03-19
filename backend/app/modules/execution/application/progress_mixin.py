"""执行进度与串行推进相关服务能力。"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from pymongo import ReturnDocument

from app.modules.execution.application.constants import (
    FINAL_CASE_STATUSES,
    STOP_MODE_AFTER_CURRENT_CASE,
    STOP_MODE_NONE,
)
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
    ExecutionTaskRunDoc,
)
from app.shared.core.mongo_client import get_mongo_client
from app.shared.db.config import settings


class ExecutionProgressMixin:
    """处理任务串行推进与轮次同步能力。"""

    @classmethod
    async def _get_case_doc_by_order(
            cls,
            task_id: str,
            order_no: int,
    ) -> ExecutionTaskCaseDoc | None:
        return await ExecutionTaskCaseDoc.find_one({"task_id": task_id, "order_no": order_no})

    @staticmethod
    async def _acquire_progress_lock(
            task_id: str,
            completed_case_id: str,
            current_case_index: int,
    ) -> ExecutionTaskDoc | None:
        """
        用原子条件更新获取推进锁，避免重复回调把下一条 case 下发多次。
        仅当任务游标仍指向已完成 case 且未持锁时才允许推进。
        """
        token = uuid.uuid4().hex
        collection = get_mongo_client()[settings.MONGO_DB_NAME][ExecutionTaskDoc.Settings.name]
        updated = await collection.find_one_and_update(
            {
                "task_id": task_id,
                "current_case_id": completed_case_id,
                "current_case_index": current_case_index,
                "orchestration_lock": None,
                "is_deleted": False,
            },
            {
                "$set": {
                    "orchestration_lock": token,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            return None
        return await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})

    @staticmethod
    async def _release_progress_lock(task_id: str) -> None:
        collection = get_mongo_client()[settings.MONGO_DB_NAME][ExecutionTaskDoc.Settings.name]
        await collection.update_one(
            {"task_id": task_id, "is_deleted": False},
            {"$set": {"orchestration_lock": None, "updated_at": datetime.now(timezone.utc)}},
        )

    async def _mark_task_completed_from_cases(self, task_doc: ExecutionTaskDoc) -> None:
        """基于用例明细自动收口任务。"""
        case_docs = await ExecutionTaskCaseDoc.find({"task_id": task_doc.task_id}).to_list()
        terminal_docs = [doc for doc in case_docs if doc.status in FINAL_CASE_STATUSES]
        if not case_docs or len(terminal_docs) != len(case_docs):
            return

        task_doc.reported_case_count = len(case_docs)
        task_doc.current_case_id = None
        task_doc.current_case_index = task_doc.case_count
        task_doc.finished_at = datetime.now(timezone.utc)
        task_doc.last_callback_at = task_doc.finished_at
        if any(doc.status == "FAILED" for doc in terminal_docs):
            task_doc.overall_status = "FAILED"
        elif any(doc.status == "PASSED" for doc in terminal_docs):
            task_doc.overall_status = "PASSED"
        else:
            task_doc.overall_status = "SKIPPED"
        if task_doc.dispatch_status != "DISPATCH_FAILED":
            task_doc.dispatch_status = "COMPLETED"
        task_doc.orchestration_lock = None
        await task_doc.save()
        await self._sync_run_from_task(task_doc)

    async def _mark_task_stopped_after_current_case(self, task_doc: ExecutionTaskDoc) -> None:
        """在当前 case 完成后执行优雅停止，不再继续下发下一条。"""
        completed_case_count = await ExecutionTaskCaseDoc.find({
            "task_id": task_doc.task_id,
            "status": {"$in": list(FINAL_CASE_STATUSES)},
        }).count()
        task_doc.reported_case_count = completed_case_count
        task_doc.current_case_id = None
        task_doc.current_case_index = min(task_doc.current_case_index + 1, task_doc.case_count)
        task_doc.finished_at = datetime.now(timezone.utc)
        task_doc.last_callback_at = task_doc.finished_at
        task_doc.overall_status = "STOPPED"
        if task_doc.dispatch_status != "DISPATCH_FAILED":
            task_doc.dispatch_status = "COMPLETED"
        task_doc.orchestration_lock = None
        await task_doc.save()
        await self._sync_run_from_task(task_doc)

    async def _sync_run_from_task(self, task_doc: ExecutionTaskDoc) -> None:
        """把任务当前结果同步到当前执行轮次。"""
        if task_doc.current_run_no <= 0:
            return

        run_doc = await ExecutionTaskRunDoc.find_one({
            "task_id": task_doc.task_id,
            "run_no": task_doc.current_run_no,
        })
        if not run_doc:
            return

        self._assign_fields(
            run_doc,
            overall_status=task_doc.overall_status,
            dispatch_status=task_doc.dispatch_status,
            dispatch_channel=task_doc.dispatch_channel,
            dispatch_response=dict(task_doc.dispatch_response or {}),
            dispatch_error=task_doc.dispatch_error,
            reported_case_count=task_doc.reported_case_count,
            stop_mode=getattr(task_doc, "stop_mode", STOP_MODE_NONE),
            stop_requested_at=getattr(task_doc, "stop_requested_at", None),
            stop_requested_by=getattr(task_doc, "stop_requested_by", None),
            stop_reason=getattr(task_doc, "stop_reason", None),
            started_at=task_doc.started_at,
            finished_at=task_doc.finished_at,
            last_callback_at=task_doc.last_callback_at,
        )
        await run_doc.save()

    async def _dispatch_next_case_if_needed(
            self,
            task_doc: ExecutionTaskDoc,
            completed_case_id: str,
    ) -> None:
        """在当前用例完成后推进下一条用例下发。"""
        if task_doc.current_case_id != completed_case_id:
            return

        locked_task_doc = await self._acquire_progress_lock(
            task_id=task_doc.task_id,
            completed_case_id=completed_case_id,
            current_case_index=task_doc.current_case_index,
        )
        if not locked_task_doc:
            return

        next_case_doc: ExecutionTaskCaseDoc | None = None
        try:
            if locked_task_doc.stop_mode == STOP_MODE_AFTER_CURRENT_CASE:
                await self._mark_task_stopped_after_current_case(locked_task_doc)
                return

            next_case_doc = await self._get_case_doc_by_order(
                locked_task_doc.task_id,
                locked_task_doc.current_case_index + 1,
            )
            if not next_case_doc:
                await self._mark_task_completed_from_cases(locked_task_doc)
                return

            locked_task_doc.current_case_id = next_case_doc.case_id
            locked_task_doc.current_case_index = next_case_doc.order_no
            locked_task_doc.consume_status = "PENDING"
            await self._dispatch_existing_task(
                locked_task_doc,
                await self._build_task_dispatch_command(locked_task_doc, next_case_doc.order_no),
            )
        finally:
            if next_case_doc:
                await self._release_progress_lock(task_doc.task_id)

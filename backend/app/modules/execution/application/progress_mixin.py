"""执行进度与串行推进相关服务能力。"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Dict

from pymongo import ReturnDocument

from app.modules.execution.application.constants import FINAL_CASE_STATUSES
from app.modules.execution.repository.models import (
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
    ExecutionTaskRunCaseDoc,
    ExecutionTaskRunDoc,
)
from app.shared.core.mongo_client import get_mongo_client
from app.shared.db.config import settings


class ExecutionProgressMixin:
    """处理任务事件、case 回报、平台推进与任务收口。"""

    @classmethod
    async def _get_case_doc_by_order(
            cls,
            task_id: str,
            order_no: int,
    ) -> ExecutionTaskCaseDoc | None:
        return await ExecutionTaskCaseDoc.find_one({"task_id": task_id, "order_no": order_no})

    @staticmethod
    async def _count_non_terminal_cases(task_id: str) -> int:
        """统计仍未到终态的用例数量。"""
        return await ExecutionTaskCaseDoc.find({
            "task_id": task_id,
            "status": {"$nin": list(FINAL_CASE_STATUSES)},
        }).count()

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

        run_doc.overall_status = task_doc.overall_status
        run_doc.dispatch_status = task_doc.dispatch_status
        run_doc.dispatch_channel = task_doc.dispatch_channel
        run_doc.dispatch_response = dict(task_doc.dispatch_response or {})
        run_doc.dispatch_error = task_doc.dispatch_error
        run_doc.reported_case_count = task_doc.reported_case_count
        run_doc.started_at = task_doc.started_at
        run_doc.finished_at = task_doc.finished_at
        run_doc.last_callback_at = task_doc.last_callback_at
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
            next_case_doc = await self._get_case_doc_by_order(
                locked_task_doc.task_id,
                locked_task_doc.current_case_index + 1,
            )
            if not next_case_doc:
                await self._mark_task_completed_from_cases(locked_task_doc)
                return

            case_ids = self._extract_case_ids_from_payload(locked_task_doc.request_payload)
            locked_task_doc.current_case_id = next_case_doc.case_id
            locked_task_doc.current_case_index = next_case_doc.order_no
            locked_task_doc.consume_status = "PENDING"
            await self._dispatch_existing_task(
                locked_task_doc,
                self._build_case_dispatch_command(
                    task_doc=locked_task_doc,
                    case_ids=case_ids,
                    dispatch_case_id=next_case_doc.case_id,
                    dispatch_case_index=next_case_doc.order_no,
                ),
            )
        finally:
            if next_case_doc:
                await self._release_progress_lock(task_doc.task_id)
    @staticmethod
    def _normalize_status(value: str, default: str = "UNKNOWN") -> str:
        """统一状态字符串格式。"""
        return (value or default).strip().upper()

    @staticmethod
    def _merge_result_payload(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        """合并执行结果扩展信息。"""
        merged = dict(base or {})
        merged.update(extra or {})
        return merged


    async def report_task_event(
            self,
            task_id: str,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """记录代理上报的原始任务事件。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        existing_event = await ExecutionEventDoc.find_one({
            "task_id": task_id,
            "event_id": payload["event_id"],
        })
        if existing_event:
            return {
                "task_id": existing_event.task_id,
                "event_id": existing_event.event_id,
                "event_type": existing_event.event_type,
                "seq": existing_event.seq,
                "received_at": existing_event.received_at,
                "processed": existing_event.processed,
            }

        source_time = payload.get("source_time")
        event_doc = ExecutionEventDoc(
            task_id=task_id,
            event_id=payload["event_id"],
            event_type=self._normalize_status(payload["event_type"], default="UNKNOWN"),
            seq=payload.get("seq", 0),
            source_time=self._ensure_utc_datetime(source_time) if source_time else None,
            raw_payload=payload.get("payload", {}),
            processed=True,
        )
        await event_doc.insert()

        task_doc.last_callback_at = datetime.now(timezone.utc)
        if event_doc.event_type in {"TASK_STARTED", "STARTED"} and not task_doc.started_at:
            task_doc.started_at = task_doc.last_callback_at
            task_doc.overall_status = "RUNNING"
        await task_doc.save()
        await self._sync_run_from_task(task_doc)

        return {
            "task_id": event_doc.task_id,
            "event_id": event_doc.event_id,
            "event_type": event_doc.event_type,
            "seq": event_doc.seq,
            "received_at": event_doc.received_at,
            "processed": event_doc.processed,
        }

    @staticmethod
    def _build_case_status_response(task_id: str, case_id: str, case_doc: ExecutionTaskCaseDoc, accepted: bool) -> Dict[str, Any]:
        """统一构造用例状态回包。"""
        return {
            "task_id": task_id,
            "case_id": case_id,
            "status": case_doc.status,
            "progress_percent": case_doc.progress_percent,
            "step_total": case_doc.step_total,
            "step_passed": case_doc.step_passed,
            "step_failed": case_doc.step_failed,
            "step_skipped": case_doc.step_skipped,
            "last_seq": case_doc.last_seq,
            "accepted": accepted,
            "started_at": case_doc.started_at,
            "finished_at": case_doc.finished_at,
            "updated_at": case_doc.updated_at,
        }

    def _apply_case_status_payload(
        self,
        case_doc: ExecutionTaskCaseDoc,
        payload: Dict[str, Any],
        normalized_status: str,
    ) -> None:
        """把回调载荷映射到 case 文档。"""
        case_doc.status = normalized_status
        if payload.get("progress_percent") is not None:
            case_doc.progress_percent = payload["progress_percent"]
        if payload.get("step_total") is not None:
            case_doc.step_total = payload["step_total"]
        if payload.get("step_passed") is not None:
            case_doc.step_passed = payload["step_passed"]
        if payload.get("step_failed") is not None:
            case_doc.step_failed = payload["step_failed"]
        if payload.get("step_skipped") is not None:
            case_doc.step_skipped = payload["step_skipped"]
        if payload.get("started_at"):
            case_doc.started_at = self._ensure_utc_datetime(payload["started_at"])
        elif not case_doc.started_at and normalized_status in {"RUNNING", *FINAL_CASE_STATUSES}:
            case_doc.started_at = datetime.now(timezone.utc)
        if payload.get("finished_at"):
            case_doc.finished_at = self._ensure_utc_datetime(payload["finished_at"])
        elif normalized_status in FINAL_CASE_STATUSES and not case_doc.finished_at:
            case_doc.finished_at = datetime.now(timezone.utc)
        if payload.get("event_id"):
            case_doc.last_event_id = payload["event_id"]
        case_doc.last_seq = payload.get("seq", 0)
        case_doc.case_snapshot = self._merge_result_payload(
            case_doc.case_snapshot,
            payload.get("result_data", {}),
        )

    async def _sync_run_case_from_case(
        self,
        task_doc: ExecutionTaskDoc,
        case_doc: ExecutionTaskCaseDoc,
        payload: Dict[str, Any],
    ) -> None:
        """把当前 case 结果同步到本轮历史记录。"""
        if task_doc.current_run_no <= 0:
            return

        run_case_doc = await ExecutionTaskRunCaseDoc.find_one({
            "task_id": task_doc.task_id,
            "run_no": task_doc.current_run_no,
            "case_id": case_doc.case_id,
        })
        if not run_case_doc:
            return

        run_case_doc.dispatch_status = case_doc.dispatch_status
        run_case_doc.dispatch_attempts = case_doc.dispatch_attempts
        run_case_doc.status = case_doc.status
        run_case_doc.progress_percent = case_doc.progress_percent
        run_case_doc.step_total = case_doc.step_total
        run_case_doc.step_passed = case_doc.step_passed
        run_case_doc.step_failed = case_doc.step_failed
        run_case_doc.step_skipped = case_doc.step_skipped
        run_case_doc.started_at = case_doc.started_at
        run_case_doc.finished_at = case_doc.finished_at
        run_case_doc.dispatched_at = case_doc.dispatched_at
        run_case_doc.last_seq = case_doc.last_seq
        run_case_doc.last_event_id = case_doc.last_event_id
        run_case_doc.result_data = self._merge_result_payload(
            run_case_doc.result_data,
            payload.get("result_data", {}),
        )
        await run_case_doc.save()

    async def _update_task_progress_from_case(self, task_doc: ExecutionTaskDoc, task_id: str) -> None:
        """根据 case 更新任务进度统计。"""
        task_doc.last_callback_at = datetime.now(timezone.utc)
        if not task_doc.started_at:
            task_doc.started_at = task_doc.last_callback_at
        if task_doc.overall_status in {"QUEUED", "DISPATCHED"}:
            task_doc.overall_status = "RUNNING"
        finished_case_count = await ExecutionTaskCaseDoc.find({
            "task_id": task_id,
            "status": {"$in": list(FINAL_CASE_STATUSES)},
        }).count()
        task_doc.reported_case_count = finished_case_count
        await task_doc.save()

    async def report_case_status(
            self,
            task_id: str,
            case_id: str,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新单个测试用例执行状态。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        case_doc = await ExecutionTaskCaseDoc.find_one({"task_id": task_id, "case_id": case_id})
        if not case_doc:
            raise KeyError(f"Task case not found: {task_id}/{case_id}")

        seq = payload.get("seq", 0)
        accepted = seq >= case_doc.last_seq
        if accepted:
            status = self._normalize_status(payload["status"], default=case_doc.status)
            self._apply_case_status_payload(case_doc, payload, status)
            await case_doc.save()
            await self._update_task_progress_from_case(task_doc, task_id)
            await self._sync_run_case_from_case(task_doc, case_doc, payload)
            await self._sync_run_from_task(task_doc)

            if status in FINAL_CASE_STATUSES:
                await self._dispatch_next_case_if_needed(task_doc, case_id)

        return self._build_case_status_response(task_id, case_id, case_doc, accepted)

    async def complete_task(
            self,
            task_id: str,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """接收任务最终完成结果。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        remaining_case_count = await self._count_non_terminal_cases(task_id)
        if remaining_case_count > 0:
            raise ValueError("Task cannot be completed before all cases reach terminal status")

        normalized_status = self._normalize_status(payload["status"], default=task_doc.overall_status)
        now = datetime.now(timezone.utc)
        finished_at = self._ensure_utc_datetime(payload["finished_at"]) if payload.get("finished_at") else now
        task_doc.overall_status = normalized_status
        task_doc.finished_at = finished_at
        task_doc.last_callback_at = now
        if not task_doc.started_at:
            task_doc.started_at = now
        if task_doc.dispatch_status != "DISPATCH_FAILED":
            task_doc.dispatch_status = "COMPLETED"
        task_doc.dispatch_response = self._merge_result_payload(task_doc.dispatch_response, payload.get("summary", {}))
        if payload.get("error_message"):
            task_doc.dispatch_error = payload["error_message"]
        if payload.get("executor"):
            task_doc.dispatch_response["executor"] = payload["executor"]
        if payload.get("event_id"):
            existing_event = await ExecutionEventDoc.find_one({
                "task_id": task_id,
                "event_id": payload["event_id"],
            })
            if not existing_event:
                await ExecutionEventDoc(
                    task_id=task_id,
                    event_id=payload["event_id"],
                    event_type="TASK_COMPLETED",
                    seq=payload.get("seq", 0),
                    source_time=finished_at,
                    raw_payload={
                        "status": normalized_status,
                        "summary": payload.get("summary", {}),
                        "error_message": payload.get("error_message"),
                    },
                    processed=True,
                ).insert()

        completed_case_count = await ExecutionTaskCaseDoc.find({
            "task_id": task_id,
            "status": {"$in": list(FINAL_CASE_STATUSES)},
        }).count()
        task_doc.reported_case_count = completed_case_count
        task_doc.current_case_id = None
        task_doc.current_case_index = task_doc.case_count
        await task_doc.save()
        await self._sync_run_from_task(task_doc)

        return {
            "task_id": task_doc.task_id,
            "overall_status": task_doc.overall_status,
            "dispatch_status": task_doc.dispatch_status,
            "consume_status": task_doc.consume_status,
            "reported_case_count": task_doc.reported_case_count,
            "started_at": task_doc.started_at,
            "finished_at": task_doc.finished_at,
            "last_callback_at": task_doc.last_callback_at,
            "updated_at": task_doc.updated_at,
        }

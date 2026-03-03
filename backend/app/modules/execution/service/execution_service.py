"""测试执行服务。"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo.errors import DuplicateKeyError

from app.modules.execution.repository.models import (
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.db.config import settings
from app.shared.service import BaseService, SequenceIdService


class ExecutionService(BaseService):
    """执行任务编排与回调处理。"""

    _ALLOWED_TASK_STATUS = {
        "QUEUED",
        "RUNNING",
        "PASSED",
        "FAILED",
        "PARTIAL_FAILED",
        "CANCELLED",
        "TIMEOUT",
    }
    _ALLOWED_CASE_STATUS = {
        "QUEUED",
        "RUNNING",
        "PASSED",
        "FAILED",
        "SKIPPED",
        "BLOCKED",
        "ERROR",
    }

    async def dispatch_task(self, payload: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        cases = payload.get("cases") or []
        if not cases:
            raise ValueError("cases must not be empty")

        case_ids = [str(item.get("case_id", "")).strip() for item in cases]
        if not all(case_ids):
            raise ValueError("case_id is required")
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("duplicate case_id in request")

        docs = await TestCaseDoc.find(
            {"case_id": {"$in": case_ids}, "is_deleted": False}
        ).to_list()
        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"case not found: {missing}")

        year = datetime.now().year
        seq = await SequenceIdService().next(f"execution_task:{year}")
        task_id = f"ET-{year}-{str(seq).zfill(6)}"

        request_payload = {
            "framework": payload.get("framework"),
            "trigger_source": payload.get("trigger_source"),
            "callback_url": payload.get("callback_url"),
            "dut": payload.get("dut") or {},
            "cases": [{"case_id": cid} for cid in case_ids],
            "runtime_config": payload.get("runtime_config") or {},
        }

        # MVP 阶段先记录“下发结果”。真正调外部框架由后续迭代接入。
        external_task_id = f"EXT-{task_id}"
        dispatch_response = {
            "accepted": True,
            "message": "dispatch accepted (mock)",
            "external_task_id": external_task_id,
        }

        task_doc = ExecutionTaskDoc(
            task_id=task_id,
            external_task_id=external_task_id,
            framework=str(payload.get("framework") or "unknown"),
            dispatch_status="DISPATCHED",
            overall_status="QUEUED",
            request_payload=request_payload,
            dispatch_response=dispatch_response,
            dispatch_error=None,
            created_by=created_by,
            case_count=len(case_ids),
            reported_case_count=0,
        )
        await task_doc.insert()

        for cid in case_ids:
            case_doc = doc_map[cid]
            snapshot = {
                "case_id": case_doc.case_id,
                "title": case_doc.title,
                "version": case_doc.version,
                "priority": case_doc.priority,
                "status": case_doc.status,
            }
            await ExecutionTaskCaseDoc(
                task_id=task_id,
                case_id=cid,
                case_snapshot=snapshot,
                status="QUEUED",
                last_seq=0,
            ).insert()

        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "dispatch_status": task_doc.dispatch_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "created_at": task_doc.created_at,
        }

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        task = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            {"is_deleted": False},
        )
        if not task:
            raise KeyError("task not found")

        stats = await self._compute_task_stats(task_id)
        data = self._doc_to_dict(task)
        data["stats"] = stats
        return data

    async def list_tasks(
        self,
        created_by: Optional[str] = None,
        framework: Optional[str] = None,
        overall_status: Optional[str] = None,
        dispatch_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = ExecutionTaskDoc.find({"is_deleted": False})
        if created_by:
            query = query.find(ExecutionTaskDoc.created_by == created_by)
        if framework:
            query = query.find(ExecutionTaskDoc.framework == framework)
        if overall_status:
            query = query.find(ExecutionTaskDoc.overall_status == overall_status)
        if dispatch_status:
            query = query.find(ExecutionTaskDoc.dispatch_status == dispatch_status)

        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def list_task_cases(
        self,
        task_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        task = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            {"is_deleted": False},
        )
        if not task:
            raise KeyError("task not found")

        query = ExecutionTaskCaseDoc.find(ExecutionTaskCaseDoc.task_id == task_id)
        if status:
            query = query.find(ExecutionTaskCaseDoc.status == status)

        docs = await query.sort("created_at").skip(offset).limit(limit).to_list()
        return [self._doc_to_dict(doc) for doc in docs]

    async def handle_progress_callback(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        framework_id = headers.get("x-framework-id")
        event_id = headers.get("x-event-id")
        timestamp = headers.get("x-timestamp")
        signature = headers.get("x-signature")

        if not framework_id or not event_id or not timestamp or not signature:
            raise PermissionError("missing signature headers")

        self._verify_signature(
            secret=settings.JWT_SECRET_KEY,
            timestamp=timestamp,
            event_id=event_id,
            raw_body=raw_body,
            signature=signature,
        )

        task_id = payload.get("task_id")
        if not task_id:
            raise ValueError("task_id is required")

        task_doc = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            {"is_deleted": False},
        )
        if not task_doc:
            raise KeyError("task not found")

        event_doc = ExecutionEventDoc(
            task_id=task_id,
            event_id=event_id,
            event_type=str(payload.get("event_type") or "UNKNOWN"),
            seq=int(payload.get("seq") or 0),
            source_time=payload.get("event_time"),
            raw_payload=payload,
            processed=False,
        )
        try:
            await event_doc.insert()
        except DuplicateKeyError:
            return {"accepted": True, "deduplicated": True}

        try:
            await self._apply_progress(task_doc, payload, event_id)
            event_doc.processed = True
            event_doc.process_error = None
            await event_doc.save()
        except Exception as exc:
            event_doc.processed = False
            event_doc.process_error = str(exc)
            await event_doc.save()
            raise

        return {"accepted": True, "deduplicated": False}

    async def _apply_progress(self, task_doc: ExecutionTaskDoc, payload: Dict[str, Any], event_id: str) -> None:
        now = datetime.now(timezone.utc)
        task_doc.last_callback_at = now

        incoming_overall = payload.get("overall_status")
        if incoming_overall:
            incoming_overall = str(incoming_overall).upper()
            if incoming_overall not in self._ALLOWED_TASK_STATUS:
                raise ValueError("invalid overall_status")
            task_doc.overall_status = incoming_overall
            if incoming_overall == "RUNNING" and task_doc.started_at is None:
                task_doc.started_at = now
            if incoming_overall in {"PASSED", "FAILED", "PARTIAL_FAILED", "CANCELLED", "TIMEOUT"}:
                task_doc.finished_at = now

        case_payload = payload.get("case") or {}
        case_id = case_payload.get("case_id")
        seq = int(payload.get("seq") or 0)

        if case_id:
            case_doc = await ExecutionTaskCaseDoc.find_one(
                ExecutionTaskCaseDoc.task_id == task_doc.task_id,
                ExecutionTaskCaseDoc.case_id == str(case_id),
            )
            if not case_doc:
                raise KeyError("task case not found")

            # 乱序保护
            if seq <= case_doc.last_seq:
                await task_doc.save()
                return

            incoming_case_status = case_payload.get("status")
            if incoming_case_status:
                incoming_case_status = str(incoming_case_status).upper()
                if incoming_case_status not in self._ALLOWED_CASE_STATUS:
                    raise ValueError("invalid case status")
                case_doc.status = incoming_case_status
                if incoming_case_status == "RUNNING" and case_doc.started_at is None:
                    case_doc.started_at = now
                if incoming_case_status in {"PASSED", "FAILED", "SKIPPED", "BLOCKED", "ERROR"}:
                    case_doc.finished_at = now

            if case_payload.get("progress_percent") is not None:
                case_doc.progress_percent = float(case_payload.get("progress_percent"))
            if case_payload.get("step_total") is not None:
                case_doc.step_total = int(case_payload.get("step_total"))
            if case_payload.get("step_passed") is not None:
                case_doc.step_passed = int(case_payload.get("step_passed"))
            if case_payload.get("step_failed") is not None:
                case_doc.step_failed = int(case_payload.get("step_failed"))
            if case_payload.get("step_skipped") is not None:
                case_doc.step_skipped = int(case_payload.get("step_skipped"))

            case_doc.last_seq = seq
            case_doc.last_event_id = event_id
            await case_doc.save()

        reported_count = await ExecutionTaskCaseDoc.find(
            ExecutionTaskCaseDoc.task_id == task_doc.task_id,
            {"last_seq": {"$gt": 0}},
        ).count()
        task_doc.reported_case_count = reported_count
        await task_doc.save()

    async def _compute_task_stats(self, task_id: str) -> Dict[str, int]:
        docs = await ExecutionTaskCaseDoc.find(ExecutionTaskCaseDoc.task_id == task_id).to_list()
        stats = {
            "queued": 0,
            "running": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "blocked": 0,
            "error": 0,
        }
        for doc in docs:
            key = (doc.status or "").lower()
            if key in stats:
                stats[key] += 1
        return stats

    @staticmethod
    def _verify_signature(
        secret: str,
        timestamp: str,
        event_id: str,
        raw_body: bytes,
        signature: str,
    ) -> None:
        try:
            ts = int(timestamp)
        except ValueError as exc:
            raise PermissionError("invalid timestamp") from exc

        now = int(time.time())
        if abs(now - ts) > 300:
            raise PermissionError("timestamp out of window")

        signing = f"{timestamp}\\n{event_id}\\n".encode("utf-8") + raw_body
        expected = hmac.new(secret.encode("utf-8"), signing, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise PermissionError("invalid signature")

from __future__ import annotations

from datetime import timezone
from typing import Any

from app.modules.execution.application.constants import FINAL_CASE_STATUSES
from app.modules.execution.application.execution_service import ExecutionService
from app.modules.execution.domain.status_rules import resolve_case_status
from app.modules.execution.repository.models import (
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.execution.schemas.kafka_events import TestEvent
from app.shared.core.logger import log as logger


class ExecutionEventIngestService:

    async def ingest_event(
        self,
        topic: str,
        event_payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> bool:
        """处理单条 Kafka 事件并同步 execution 相关视图。

        主流程：
        1. 解析事件
        2. 基于 event_id 做幂等
        3. 归档原始事件
        4. 更新当前态 case / task
        """
        event = TestEvent.model_validate(event_payload)
        logger.debug(
            "Ingesting execution event: "
            f"topic={topic}, task_id={event.task_id}, case_id={event.case_id}, "
            f"event_id={event.event_id}, event_type={event.event_type}, "
            f"phase={event.phase}, offset={metadata.get('offset')}"
        )
        existing = await ExecutionEventDoc.find_one({"event_id": event.event_id})
        if existing is not None:
            # 重复事件直接跳过，避免 Kafka 重投导致重复累计。
            logger.debug(
                f"Skipping duplicate execution event: event_id={event.event_id}, task_id={event.task_id}"
            )
            return False

        event_time = event.timestamp.astimezone(timezone.utc)
        task_doc = await ExecutionTaskDoc.find_one({"task_id": event.task_id, "is_deleted": False})
        if task_doc is None:
            # 任务不存在时仍归档事件，方便后续排查来源或做补偿处理。
            logger.warning(
                f"Execution task not found for event: task_id={event.task_id}, event_id={event.event_id}"
            )
            await self._archive_event(
                topic=topic,
                event=event,
                metadata=metadata,
                processed=False,
                process_error=f"Execution task not found: {event.task_id}",
            )
            return False

        await self._archive_event(
            topic=topic,
            event=event,
            metadata=metadata,
            processed=True,
            process_error=None,
        )

        case_doc = None
        if event.case_id:
            case_doc = await ExecutionTaskCaseDoc.find_one({
                "task_id": event.task_id,
                "case_id": event.case_id,
            })
            if case_doc is None:
                logger.warning(
                    "Execution case not found for event: "
                    f"task_id={event.task_id}, case_id={event.case_id}, event_id={event.event_id}"
                )

        case_status = resolve_case_status(
            event_type=event.event_type,
            phase=event.phase,
            event_status=event.status,
            failed_cases=event.failed_cases,
        )
        if case_doc is not None:
            self._apply_case_event(
                target=case_doc,
                event=event,
                event_time=event_time,
                resolved_status=case_status,
            )
            await case_doc.save()
            logger.debug(
                "Updated execution case from event: "
                f"task_id={case_doc.task_id}, case_id={case_doc.case_id}, "
                f"status={case_doc.status}, progress={case_doc.progress_percent}, "
                f"event_count={case_doc.event_count}"
            )

        self._apply_task_aggregate(task_doc, event, event_time)
        await task_doc.save()
        logger.debug(
            "Updated execution task aggregate from event: "
            f"task_id={task_doc.task_id}, overall_status={task_doc.overall_status}, "
            f"current_case_id={getattr(task_doc, 'current_case_id', None)}, "
            f"current_case_index={getattr(task_doc, 'current_case_index', None)}, "
            f"finished_case_count={task_doc.finished_case_count}, "
            f"failed_case_count={task_doc.failed_case_count}, "
            f"progress={task_doc.progress_percent}"
        )
        await self._advance_task_after_case_finish(
            task_doc=task_doc,
            case_doc=case_doc,
            event=event,
            event_time=event_time,
            resolved_case_status=case_status,
        )

        return True

    async def _archive_event(
        self,
        topic: str,
        event: TestEvent,
        metadata: dict[str, Any],
        processed: bool,
        process_error: str | None,
    ) -> None:
        """归档原始事件。

        这张表既用于 event_id 幂等，也用于调试、审计和后续回放。
        """
        await ExecutionEventDoc(
            event_id=event.event_id,
            task_id=event.task_id,
            case_id=event.case_id,
            topic=topic,
            schema_name=event.schema_name,
            event_type=event.event_type,
            phase=event.phase,
            event_seq=event.event_seq,
            event_status=event.status,
            event_timestamp=event.timestamp.astimezone(timezone.utc),
            payload=event.model_dump(mode="json"),
            metadata=metadata,
            processed=processed,
            process_error=process_error,
        ).insert()

    @staticmethod
    def _apply_case_event(
        target: Any,
        event: TestEvent,
        event_time,
        resolved_status: str | None,
    ) -> None:
        """将单条事件映射到 case 当前态。"""
        target.last_event_id = event.event_id
        target.last_event_at = event_time
        target.event_count = getattr(target, "event_count", 0) + 1
        if event.event_seq is not None:
            target.last_seq = max(getattr(target, "last_seq", 0), event.event_seq)
        if event.case_title:
            target.case_title_snapshot = event.case_title
        if event.project_tag:
            target.project_tag = event.project_tag
        if event.nodeid:
            target.nodeid = event.nodeid
        ExecutionEventIngestService._apply_case_phase_timestamps(target, event, event_time)
        ExecutionEventIngestService._apply_assert_counters(target, event)
        if resolved_status is not None:
            target.status = resolved_status
        ExecutionEventIngestService._apply_failure_message(target, event)
        existing_assertions = ExecutionEventIngestService._build_assertion_history(
            target=target,
            event=event,
            event_time=event_time,
        )
        target.result_data = {
            **dict(getattr(target, "result_data", {}) or {}),
            "event_type": event.event_type,
            "phase": event.phase,
            "status": event.status,
            "total_cases": event.total_cases,
            "started_cases": event.started_cases,
            "finished_cases": event.finished_cases,
            "failed_cases": event.failed_cases,
            "assertions": existing_assertions,
            "data": dict(event.data or {}),
            "error": dict(event.error or {}),
        }
        if event.total_cases:
            target.progress_percent = round((event.finished_cases / event.total_cases) * 100, 2)

    @staticmethod
    def _apply_case_phase_timestamps(target: Any, event: TestEvent, event_time) -> None:
        """根据 progress 事件的 phase 补全 case 的开始/结束时间。"""
        if event.phase == "case_start" and getattr(target, "started_at", None) is None:
            target.started_at = event_time
        if event.phase == "case_finish":
            if getattr(target, "started_at", None) is None:
                target.started_at = event_time
            target.finished_at = event_time

    @staticmethod
    def _apply_assert_counters(target: Any, event: TestEvent) -> None:
        """assert 事件会累积步骤统计。"""
        if event.event_type != "assert":
            return
        target.step_total = getattr(target, "step_total", 0) + 1
        normalized_status = (event.status or "").strip().lower()
        if normalized_status == "ok":
            target.step_passed = getattr(target, "step_passed", 0) + 1
        elif normalized_status == "failed":
            target.step_failed = getattr(target, "step_failed", 0) + 1
        elif normalized_status == "skipped":
            target.step_skipped = getattr(target, "step_skipped", 0) + 1

    @staticmethod
    def _apply_failure_message(target: Any, event: TestEvent) -> None:
        """优先采用断言错误消息，否则退化为 status。"""
        if event.error.get("message"):
            target.failure_message = event.error["message"]
        elif event.status and event.status.upper() == "FAILED":
            target.failure_message = event.status

    @staticmethod
    def _build_assertion_history(target: Any, event: TestEvent, event_time) -> list[dict[str, Any]]:
        """把 assert 事件追加到断言明细列表中，供前端做步骤展示。"""
        existing_assertions = list(dict(getattr(target, "result_data", {}) or {}).get("assertions", []))
        if event.event_type != "assert":
            return existing_assertions
        existing_assertions.append({
            "seq": event.event_seq,
            "name": event.assert_name,
            "status": event.status,
            "data": dict(event.data or {}),
            "error": dict(event.error or {}),
            "timestamp": event_time.isoformat(),
        })
        return existing_assertions

    @staticmethod
    def _apply_task_aggregate(task_doc: Any, event: TestEvent, event_time) -> None:
        """把单条事件聚合到任务当前态。"""
        task_doc.last_event_id = event.event_id
        task_doc.last_event_at = event_time
        task_doc.last_event_type = event.event_type
        task_doc.last_event_phase = event.phase
        task_doc.consumed_at = event_time
        task_doc.consume_status = "CONSUMED"
        task_doc.started_case_count = max(getattr(task_doc, "started_case_count", 0), event.started_cases)
        task_doc.finished_case_count = max(getattr(task_doc, "finished_case_count", 0), event.finished_cases)
        task_doc.failed_case_count = max(getattr(task_doc, "failed_case_count", 0), event.failed_cases)
        task_doc.passed_case_count = max(
            getattr(task_doc, "passed_case_count", 0),
            max((event.finished_cases or 0) - (event.failed_cases or 0), 0),
        )
        task_doc.reported_case_count = task_doc.finished_case_count
        if event.total_cases:
            task_doc.progress_percent = round((event.finished_cases / event.total_cases) * 100, 2)
        if event.phase == "case_start" and getattr(task_doc, "started_at", None) is None:
            task_doc.started_at = event_time
        if event.phase == "task_finish" or (
            event.total_cases > 0 and event.finished_cases >= event.total_cases
        ):
            task_doc.finished_at = event_time
            task_doc.overall_status = "FAILED" if event.failed_cases > 0 else "PASSED"
        elif event.phase in {"collection_start", "case_start", "collection_finish", "case_finish"}:
            task_doc.overall_status = "RUNNING"
        task_doc.last_callback_at = event_time

    async def _advance_task_after_case_finish(
        self,
        task_doc: Any,
        case_doc: Any,
        event: TestEvent,
        event_time,
        resolved_case_status: str | None,
    ) -> None:
        """在当前 case 完成后决定是否推进下一条，或直接收口任务。"""
        if event.event_type != "progress" or event.phase != "case_finish":
            return
        if case_doc is None or resolved_case_status not in FINAL_CASE_STATUSES:
            logger.debug(
                "Skipping task auto-advance because case is not final: "
                f"task_id={task_doc.task_id}, case_id={event.case_id}, "
                f"resolved_case_status={resolved_case_status}"
            )
            return
        if event.case_id != getattr(task_doc, "current_case_id", None):
            logger.debug(
                "Skipping task auto-advance because event case is not current: "
                f"task_id={task_doc.task_id}, event_case_id={event.case_id}, "
                f"current_case_id={task_doc.current_case_id}"
            )
            return

        next_case_index = getattr(task_doc, "current_case_index", 0) + 1
        if next_case_index >= task_doc.case_count:
            task_doc.current_case_id = None
            task_doc.current_case_index = task_doc.case_count
            task_doc.finished_at = event_time
            task_doc.last_callback_at = event_time
            task_doc.overall_status = "FAILED" if task_doc.failed_case_count > 0 else "PASSED"
            if task_doc.dispatch_status != "DISPATCH_FAILED":
                task_doc.dispatch_status = "COMPLETED"
            await task_doc.save()
            logger.info(
                "Execution task completed after final case: "
                f"task_id={task_doc.task_id}, final_case_id={event.case_id}, "
                f"overall_status={task_doc.overall_status}"
            )
            return

        service = ExecutionService()
        command = await service._build_task_dispatch_command(task_doc, next_case_index)
        logger.info(
            "Auto-dispatching next execution case: "
            f"task_id={task_doc.task_id}, finished_case_id={event.case_id}, "
            f"next_case_id={command.dispatch_case_id}, next_case_index={next_case_index}"
        )
        await service._dispatch_existing_task(task_doc, command)

from __future__ import annotations

from datetime import timezone
from typing import Any

from app.modules.execution.domain.status_rules import resolve_case_status
from app.modules.execution.repository.models import (
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
    ExecutionTaskRunCaseDoc,
    ExecutionTaskRunDoc,
)
from app.modules.execution.schemas.kafka_events import TestEvent


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
        5. 更新历史态 run_case / run
        """
        event = TestEvent.model_validate(event_payload)
        existing = await ExecutionEventDoc.find_one({"event_id": event.event_id})
        if existing is not None:
            # 重复事件直接跳过，避免 Kafka 重投导致重复累计。
            return False

        event_time = event.timestamp.astimezone(timezone.utc)
        run_no = event.run_no
        task_doc = await ExecutionTaskDoc.find_one({"task_id": event.task_id, "is_deleted": False})
        if task_doc is None:
            # 任务不存在时仍归档事件，方便后续排查来源或做补偿处理。
            await self._archive_event(
                topic=topic,
                event=event,
                metadata=metadata,
                run_no=run_no,
                processed=False,
                process_error=f"Execution task not found: {event.task_id}",
            )
            return False

        if run_no is None:
            # 执行端未显式回传 run_no 时，退化为使用任务当前轮次。
            run_no = getattr(task_doc, "current_run_no", None)

        await self._archive_event(
            topic=topic,
            event=event,
            metadata=metadata,
            run_no=run_no,
            processed=True,
            process_error=None,
        )

        case_doc = None
        run_doc = None
        run_case_doc = None
        if event.case_id:
            # 当前态 case：用于任务详情页展示和平台运行时编排。
            case_doc = await ExecutionTaskCaseDoc.find_one({
                "task_id": event.task_id,
                "case_id": event.case_id,
            })
        if run_no is not None:
            # 历史态 run / run_case：用于保留某一轮执行的完整历史。
            run_doc = await ExecutionTaskRunDoc.find_one({
                "task_id": event.task_id,
                "run_no": run_no,
            })
            if event.case_id:
                run_case_doc = await ExecutionTaskRunCaseDoc.find_one({
                    "task_id": event.task_id,
                    "run_no": run_no,
                    "case_id": event.case_id,
                })

        case_status = resolve_case_status(
            event_type=event.event_type,
            phase=event.phase,
            event_status=event.status,
            failed_cases=event.failed_cases,
        )
        # 这里得到的是“事件推导出的 case 状态”，例如：
        # - case_start -> RUNNING
        # - case_finish + failed_cases > 0 -> FAILED
        # - assert 事件通常不直接改变 case 终态
        if case_doc is not None:
            # 回填当前态 case。
            self._apply_case_event(
                target=case_doc,
                event=event,
                event_time=event_time,
                run_no=run_no,
                resolved_status=case_status,
            )
            await case_doc.save()
        if run_case_doc is not None:
            # 回填历史态 case。
            self._apply_case_event(
                target=run_case_doc,
                event=event,
                event_time=event_time,
                run_no=run_no,
                resolved_status=case_status,
            )
            run_case_doc.phase = event.phase
            await run_case_doc.save()

        self._apply_task_aggregate(task_doc, event, event_time, run_no)
        await task_doc.save()

        if run_doc is not None:
            # run 级别单独维护聚合统计，便于历史轮次查询。
            self._apply_run_aggregate(run_doc, event, event_time)
            await run_doc.save()

        return True

    async def _archive_event(
        self,
        topic: str,
        event: TestEvent,
        metadata: dict[str, Any],
        run_no: int | None,
        processed: bool,
        process_error: str | None,
    ) -> None:
        """归档原始事件。

        这张表既用于 event_id 幂等，也用于调试、审计和后续回放。
        """
        await ExecutionEventDoc(
            event_id=event.event_id,
            task_id=event.task_id,
            run_no=run_no,
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
        run_no: int | None,
        resolved_status: str | None,
    ) -> None:
        """将单条事件映射到 case 当前态或历史态。"""
        # run_no 记录这条 case 数据属于哪一轮执行。当前态和历史态都会保留。
        target.run_no = run_no
        # 最近一次处理到的事件指针，用于追踪问题和后续乱序处理。
        target.last_event_id = event.event_id
        target.last_event_at = event_time
        target.event_count = getattr(target, "event_count", 0) + 1
        if event.event_seq is not None:
            # 对支持顺序号的事件，保留已接受的最大 seq。
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
            # progress 事件会把 case 推进到 RUNNING / PASSED / FAILED 等状态。
            target.status = resolved_status
        ExecutionEventIngestService._apply_failure_message(target, event)
        existing_assertions = ExecutionEventIngestService._build_assertion_history(
            target=target,
            event=event,
            event_time=event_time,
        )
        # result_data 作为扩展结果容器，保留最近一次事件的统计信息，
        # 同时把 assert 事件累积到 assertions 列表中，供前端展示断言明细。
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
            # 用 finished/total 给当前 case 一个粗粒度进度展示。
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
        # 把单条 assert 当作一个步骤结果，用于统计该 case 执行细节。
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
        # 每条 assert 保留最小必要字段：
        # - seq: 执行顺序
        # - name: 断言名称
        # - status: ok/failed/skipped
        # - data/error: 业务上下文和失败详情
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
    def _apply_task_aggregate(task_doc: Any, event: TestEvent, event_time, run_no: int | None) -> None:
        """把单条事件聚合到任务当前态。"""
        task_doc.current_run_no = run_no or getattr(task_doc, "current_run_no", 0)
        task_doc.last_event_id = event.event_id
        task_doc.last_event_at = event_time
        task_doc.last_event_type = event.event_type
        task_doc.last_event_phase = event.phase
        # 只要消息被成功接收并处理，就认为任务已经被消费者消费过。
        task_doc.consumed_at = event_time
        task_doc.consume_status = "CONSUMED"
        # started/finished/failed/passed 都采用事件里的聚合值做“向前推进”，
        # 不回退，避免乱序或重复消息把统计冲掉。
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
            # 任务级收口：全部 case 完成后，根据失败数判定整轮最终结果。
            task_doc.finished_at = event_time
            task_doc.overall_status = "FAILED" if event.failed_cases > 0 else "PASSED"
        elif event.phase in {"collection_start", "case_start", "collection_finish", "case_finish"}:
            # 任务只要进入 case_start/case_finish，就认为本轮已经进入运行态。
            task_doc.overall_status = "RUNNING"
        task_doc.last_callback_at = event_time

    @staticmethod
    def _apply_run_aggregate(run_doc: Any, event: TestEvent, event_time) -> None:
        """把单条事件聚合到某一轮 run 的历史结果。"""
        run_doc.last_event_at = event_time
        run_doc.event_count = getattr(run_doc, "event_count", 0) + 1
        # run 级统计和 task 当前态采用同样的“只前进不回退”策略。
        run_doc.started_case_count = max(getattr(run_doc, "started_case_count", 0), event.started_cases)
        run_doc.finished_case_count = max(getattr(run_doc, "finished_case_count", 0), event.finished_cases)
        run_doc.failed_case_count = max(getattr(run_doc, "failed_case_count", 0), event.failed_cases)
        run_doc.passed_case_count = max(
            getattr(run_doc, "passed_case_count", 0),
            max((event.finished_cases or 0) - (event.failed_cases or 0), 0),
        )
        run_doc.reported_case_count = run_doc.finished_case_count
        if event.total_cases:
            run_doc.progress_percent = round((event.finished_cases / event.total_cases) * 100, 2)
        if event.phase == "case_start" and getattr(run_doc, "started_at", None) is None:
            run_doc.started_at = event_time
        if event.phase == "task_finish" or (
            event.total_cases > 0 and event.finished_cases >= event.total_cases
        ):
            run_doc.finished_at = event_time
            run_doc.overall_status = "FAILED" if event.failed_cases > 0 else "PASSED"
        else:
            run_doc.overall_status = "RUNNING"
        run_doc.last_callback_at = event_time

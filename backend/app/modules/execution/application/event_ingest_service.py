from __future__ import annotations

from datetime import timezone
from typing import Any

from app.modules.execution.application.progress_coordinator import ExecutionProgressCoordinator
from app.modules.execution.domain.status_rules import resolve_case_status
from app.modules.execution.repository.models import (
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.execution.schemas.kafka_events import TestEvent
from app.shared.core.logger import log as logger


class ExecutionEventIngestService:
    """消费 execution 相关 Kafka 事件，并把事件同步回平台当前态。

    这个服务的职责不是保存“完整历史执行过程”本身，而是把外部执行端上报的事件
    映射为平台可直接查询的当前任务状态和当前 case 状态。

    它主要维护三类数据：

    1. `ExecutionEventDoc`
       保存原始事件归档，用于幂等、审计、排障和后续回放
    2. `ExecutionTaskCaseDoc`
       保存任务内每条 case 的当前状态、最近事件、断言统计和结果摘要
    3. `ExecutionTaskDoc`
       保存整个任务的当前游标、聚合进度、整体状态，以及是否要继续推进到下一条 case
    """

    def __init__(self, progress_coordinator: ExecutionProgressCoordinator | None = None) -> None:
        self._progress_coordinator = progress_coordinator or ExecutionProgressCoordinator()

    async def ingest_event(
        self,
        topic: str,
        event_payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> bool:
        """处理单条 Kafka 事件，并同步更新 execution 的当前态视图。

        主流程：
        1. 解析事件
        2. 基于 event_id 做幂等
        3. 归档原始事件
        4. 更新当前态 case / task

        Returns:
            bool:
            - `True` 表示本次事件被成功消费并应用
            - `False` 表示事件被跳过，例如重复事件或找不到对应任务

        设计要点：
            - 即使任务不存在，也会归档事件，避免丢失排障线索
            - case 和 task 的更新分开进行，避免把局部失败放大成整条消息不可追踪
            - 是否推进下一条 case，只在 case_finish 这种“可判定当前 case 已结束”的事件上执行
        """
        # 先把原始 payload 校验成统一的事件模型，后续逻辑全部围绕强类型字段展开。
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

        # 统一使用事件上报时间作为平台侧状态更新时间，避免混用本地接收时间。
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

        # 先归档再更新当前态。这样即使后续聚合逻辑有问题，原始事件也不会丢。
        await self._archive_event(
            topic=topic,
            event=event,
            metadata=metadata,
            processed=True,
            process_error=None,
        )

        case_doc = None
        if event.case_id:
            # case_id 是可选的，因为有些任务级事件不一定绑定到单条 case。
            case_doc = await ExecutionTaskCaseDoc.find_one({
                "task_id": event.task_id,
                "case_id": event.case_id,
            })
            if case_doc is None:
                logger.warning(
                    "Execution case not found for event: "
                    f"task_id={event.task_id}, case_id={event.case_id}, event_id={event.event_id}"
                )

        # 把外部事件语义映射为平台统一 case 状态，例如 RUNNING/PASSED/FAILED。
        case_status = resolve_case_status(
            event_type=event.event_type,
            phase=event.phase,
            event_status=event.status,
            failed_cases=event.failed_cases,
        )
        if case_doc is not None:
            # case 当前态更新只在 case 文档存在时执行；不存在时只记录警告，不阻塞任务聚合。
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

        # 无论是否找到 case 文档，任务级聚合都要继续做，因为任务整体进度仍然有意义。
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
        # case_finish 后需要判断是任务结束，还是自动推进到下一条 case。
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

        这里存的是“收到什么就归档什么”的原则：
            - 尽量不在归档层丢信息
            - 处理成功与否通过 `processed/process_error` 标记区分
            - 后续若要做补偿，可以直接从归档记录重放
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
        """将单条事件映射到 case 当前态。

        这个函数只负责“当前态覆盖和累积”，不负责判断是否推进下一条。
        也就是说，它关心的是：
            - 最近收到的是什么事件
            - case 当前显示成什么状态
            - 断言统计累积到多少
            - 前端详情里展示什么 result_data
        """
        # 先更新最近一次事件元信息，便于前端和排障界面快速定位最新进展。
        target.last_event_id = event.event_id
        target.last_event_at = event_time
        target.event_count = getattr(target, "event_count", 0) + 1
        if event.event_seq is not None:
            # 事件序号只允许前进，避免乱序事件把 last_seq 回退。
            target.last_seq = max(getattr(target, "last_seq", 0), event.event_seq)
        if event.case_title:
            target.case_title_snapshot = event.case_title
        if event.project_tag:
            target.project_tag = event.project_tag
        if event.nodeid:
            target.nodeid = event.nodeid
        # 时间戳、断言统计和失败信息拆成独立函数，降低主流程复杂度。
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
        # result_data 不是完整历史，而是“当前可展示摘要 + 最近事件关键信息”。
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
            # 这里的进度是按任务总 case 数近似表达当前 case 所在事件时刻的完成度。
            target.progress_percent = round((event.finished_cases / event.total_cases) * 100, 2)

    @staticmethod
    def _apply_case_phase_timestamps(target: Any, event: TestEvent, event_time) -> None:
        """根据 progress 事件的 phase 补全 case 的开始/结束时间。

        规则：
            - `case_start` 首次出现时补 started_at
            - `case_finish` 出现时补 finished_at
            - 如果收到 finish 时还没有 start，也兜底把 started_at 设成 finish 时间，
              避免时间字段出现不完整状态
        """
        if event.phase == "case_start" and getattr(target, "started_at", None) is None:
            target.started_at = event_time
        if event.phase == "case_finish":
            if getattr(target, "started_at", None) is None:
                target.started_at = event_time
            target.finished_at = event_time

    @staticmethod
    def _apply_assert_counters(target: Any, event: TestEvent) -> None:
        """把 assert 事件折算为步骤级统计。

        平台不保存框架内部完整步骤树，而是用断言事件近似表达：
            - `step_total`
            - `step_passed`
            - `step_failed`
            - `step_skipped`
        """
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
        """提炼 case 失败信息，优先保留最有排障价值的错误文本。"""
        # error.message 一般比 status 文本更具体，因此优先采用。
        if event.error.get("message"):
            target.failure_message = event.error["message"]
        elif event.status and event.status.upper() == "FAILED":
            target.failure_message = event.status

    @staticmethod
    def _build_assertion_history(target: Any, event: TestEvent, event_time) -> list[dict[str, Any]]:
        """把 assert 事件追加到断言明细列表中，供前端做步骤展示。

        这里保留的是轻量历史：
            - 只累积 assert 事件
            - 非 assert 事件直接返回原列表
            - 不做去重，默认依赖 event_id 幂等在更上层保证不会重复进入这里
        """
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
        """把单条事件聚合到任务当前态。

        任务当前态关注的是整体执行进度，而不是单条 case 细节，因此这里主要维护：
            - 最近事件信息
            - consume_status / consumed_at
            - started/finished/failed/passed case 数
            - overall_status
            - 任务级进度百分比
        """
        # 最近事件元信息，用于任务详情页快速展示“最后一条发生了什么”。
        task_doc.last_event_id = event.event_id
        task_doc.last_event_at = event_time
        task_doc.last_event_type = event.event_type
        task_doc.last_event_phase = event.phase
        # 只要有事件成功进入聚合，说明下游已经真实消费过该任务。
        task_doc.consumed_at = event_time
        task_doc.consume_status = "CONSUMED"
        # 这里统一使用 max，避免乱序事件把聚合计数倒退。
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
        # task_finish 或“全部 case 都已完成”都可以视为任务结束信号。
        if event.phase == "task_finish" or (
            event.total_cases > 0 and event.finished_cases >= event.total_cases
        ):
            task_doc.finished_at = event_time
            task_doc.overall_status = "FAILED" if event.failed_cases > 0 else "PASSED"
        # 这些 phase 说明任务仍在运行过程中。
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
        """在当前 case 完成后决定是否推进下一条，或直接收口任务。

        这是平台串行编排的关键函数。

        触发条件很严格：
            - 必须是 `progress + case_finish`
            - 当前 case 必须已进入最终状态
            - 事件里的 case_id 必须等于任务当前游标指向的 case_id

        只有满足这些条件，平台才会认为：
            “当前正在跑的这条 case 确实结束了，可以考虑推进下一条”
        """
        await self._progress_coordinator.advance_after_case_finish(
            task_doc=task_doc,
            case_doc=case_doc,
            event=event,
            event_time=event_time,
            resolved_case_status=resolved_case_status,
        )

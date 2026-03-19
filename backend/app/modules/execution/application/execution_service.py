"""执行任务应用服务。

这个文件负责 execution 模块里的“写操作”主流程，重点处理：

- 创建执行任务
- 修改/取消尚未触发的定时任务
- 重试已有任务
- 触发首条 case 的真实下发

这里不直接承接任务查询逻辑，那部分由
`ExecutionTaskQueryMixin` 负责。
当前类更像 execution 模块的命令门面，负责把用户输入的命令
映射为任务主表、当前态明细表和历史轮次表上的一致更新。
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List

from app.modules.execution.application.agent_mixin import ExecutionAgentMixin
from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.constants import (
    FINAL_TASK_STATUSES,
    STOP_MODE_AFTER_CURRENT_CASE,
    STOP_MODE_NONE, FINAL_CASE_STATUSES,
)
from app.modules.execution.application.progress_mixin import ExecutionProgressMixin
from app.modules.execution.application.query_mixin import ExecutionTaskQueryMixin
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
    ExecutionTaskRunCaseDoc,
    ExecutionTaskRunDoc,
)
from app.modules.execution.service.task_dispatcher import ExecutionTaskDispatcher
from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc
from app.shared.core.logger import log as logger


class ExecutionService(ExecutionProgressMixin, ExecutionTaskQueryMixin, ExecutionAgentMixin):
    """执行任务命令服务。

    设计上，这个类有两个核心职责：

    1. 维护任务的“当前态”
       包括 `ExecutionTaskDoc` 和 `ExecutionTaskCaseDoc`，用于实时编排。
    2. 在关键时点生成任务“历史态”
       包括 `ExecutionTaskRunDoc` 和 `ExecutionTaskRunCaseDoc`，用于追溯每一轮执行。

    因为 execution 模块采用“平台串行推进 case”的模型，所以这里的大部分
    方法都围绕“当前该下发哪条 case”“什么时候创建新 run”“什么时候允许修改”
    这几个问题展开。
    """

    def __init__(self) -> None:
        self._dispatcher = ExecutionTaskDispatcher()

    @staticmethod
    def _assign_fields(target: Any, **values: Any) -> None:
        for field_name, field_value in values.items():
            setattr(target, field_name, field_value)

    @staticmethod
    def _build_dedup_key(command: DispatchExecutionTaskCommand) -> str:
        """基于业务载荷构建稳定去重键。

        去重目标不是“完全相同的 task_id”，而是“语义上相同、且尚未结束的任务”。
        也就是说，只要执行框架、代理、触发方式、调度时间、DUT、运行配置和 case 集
        合一致，就会得到同一个 dedup_key。

        注意这里对 `case_ids` 做了排序，故意忽略传入顺序差异，避免同一批 case
        因顺序不同被误判为不同任务。
        """
        payload = {
            "framework": command.framework,
            "agent_id": command.agent_id,
            "trigger_source": command.trigger_source,
            "schedule_type": command.schedule_type,
            "planned_at": command.planned_at.isoformat() if command.planned_at else None,
            "callback_url": command.callback_url,
            "dut": command.dut or {},
            "case_ids": sorted(command.case_ids),
        }
        normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_utc_datetime(value: datetime | str) -> datetime:
        """将 naive/aware datetime 或 ISO 时间字符串统一规范为 UTC aware datetime。

        execution 模块会把计划时间、触发时间、完成时间都落库；如果这里不统一时区，
        定时调度和状态判断会在不同时区输入下变得不可预测。
        """
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.endswith("Z"):
                normalized = f"{normalized[:-1]}+00:00"
            value = datetime.fromisoformat(normalized)
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _normalize_schedule(
            cls,
            schedule_type: str | None,
            planned_at: datetime | None,
            now: datetime | None = None,
    ) -> tuple[str, datetime | None, str, bool]:
        """统一调度类型和状态。

        返回值依次表示：

        - 归一化后的 `schedule_type`
        - 归一化后的 `planned_at`
        - 初始 `schedule_status`
        - 是否应该立刻触发首条 case 下发

        规则很简单：

        - `IMMEDIATE` 一律视为立即可执行
        - `SCHEDULED` 且 `planned_at` 已到或已过，也视为立刻可执行
        - `SCHEDULED` 且尚未到点，则进入 `PENDING`
        """
        current_time = cls._ensure_utc_datetime(now or datetime.now(timezone.utc))
        normalized_type = (schedule_type or "IMMEDIATE").upper()
        normalized_planned_at = cls._ensure_utc_datetime(planned_at) if planned_at else None

        if normalized_type == "SCHEDULED":
            if normalized_planned_at is None:
                raise ValueError("planned_at is required when schedule_type is SCHEDULED")
            if normalized_planned_at <= current_time:
                return normalized_type, normalized_planned_at, "READY", True
            return normalized_type, normalized_planned_at, "PENDING", False

        return "IMMEDIATE", normalized_planned_at, "READY", True

    @staticmethod
    async def _load_case_docs(case_ids: List[str]) -> Dict[str, Any]:
        """加载并校验任务关联的测试用例。

        这里在任务创建/修改前先把 case 全量查出来，目的有两个：

        - 提前失败，避免创建出引用不存在 case 的脏任务
        - 为后续生成 `ExecutionTaskCaseDoc.case_snapshot` 提供源数据
        """
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"Test cases not found: {missing}")
        return doc_map

    @staticmethod
    async def resolve_case_ids_by_auto_case_ids(auto_case_ids: List[str]) -> List[str]:
        """将 auto_case_id 列表解析为平台测试用例 case_id，保留原始顺序。"""
        auto_docs = await AutomationTestCaseDoc.find({
            "auto_case_id": {"$in": auto_case_ids},
            "is_deleted": False,
        }).to_list()
        source_mapping = {doc.auto_case_id: doc.source_case_id for doc in auto_docs}

        missing_auto_case_ids = [auto_case_id for auto_case_id in auto_case_ids if auto_case_id not in source_mapping]
        if missing_auto_case_ids:
            raise KeyError(f"Automation test cases not found: {missing_auto_case_ids}")

        source_case_ids = [source_mapping[auto_case_id] for auto_case_id in auto_case_ids]
        docs = await TestCaseDoc.find({
            "case_id": {"$in": source_case_ids},
            "is_deleted": False,
        }).to_list()

        mapping: Dict[str, List[str]] = {}
        for doc in docs:
            source_case_id = getattr(doc, "case_id", None)
            if not source_case_id:
                continue
            mapping.setdefault(source_case_id, []).append(doc.case_id)

        missing_source_case_ids = [source_case_id for source_case_id in source_case_ids if source_case_id not in mapping]
        if missing_source_case_ids:
            missing_auto_case_ids = [
                auto_case_id for auto_case_id in auto_case_ids
                if source_mapping.get(auto_case_id) in missing_source_case_ids
            ]
            raise KeyError(
                "Automation test cases source_case_id not matched to test cases: "
                f"auto_case_ids={missing_auto_case_ids}, source_case_ids={missing_source_case_ids}"
            )

        ambiguous = {
            source_case_id: case_ids
            for source_case_id, case_ids in mapping.items()
            if len(case_ids) > 1
        }
        if ambiguous:
            raise ValueError(f"Automation test cases linked to multiple test cases: {ambiguous}")

        return [mapping[source_mapping[auto_case_id]][0] for auto_case_id in auto_case_ids]

    @staticmethod
    async def resolve_auto_case_ids_by_case_ids(case_ids: List[str]) -> List[str]:
        """根据平台 case_id 反查 auto_case_id，保留原始顺序。"""
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False,
        }).to_list()
        source_mapping: Dict[str, str] = {}
        missing: List[str] = []
        for doc in docs:
            source_case_id = getattr(doc, "case_id", None)
            if source_case_id:
                source_mapping[doc.case_id] = source_case_id
        for case_id in case_ids:
            if case_id not in source_mapping:
                missing.append(case_id)
        if missing:
            raise KeyError(f"Test cases not linked to automation test cases: {missing}")

        auto_docs = await AutomationTestCaseDoc.find({
            "source_case_id": {"$in": list(source_mapping.values())},
            "is_deleted": False,
        }).to_list()
        auto_mapping = {doc.source_case_id: doc.auto_case_id for doc in auto_docs}
        missing_sources = [source_case_id for source_case_id in source_mapping.values() if source_case_id not in auto_mapping]
        if missing_sources:
            missing_case_ids = [case_id for case_id, source_case_id in source_mapping.items() if source_case_id in missing_sources]
            raise KeyError(f"Test cases not linked to automation test cases: {missing_case_ids}")
        return [auto_mapping[source_mapping[case_id]] for case_id in case_ids]

    @staticmethod
    def _build_task_request_payload(command: DispatchExecutionTaskCommand) -> Dict[str, Any]:
        """构建任务级快照，保留完整 case 列表用于后续串行推进。

        `request_payload` 是任务创建时的业务快照，不只是为了转发给外部执行端。
        后续重试、继续推进下一条 case、修改计划任务时，都会从这里恢复原始上下文。
        """
        return {
            "task_id": command.task_id,
            "external_task_id": command.external_task_id,
            "framework": command.framework,
            "trigger_source": command.trigger_source,
            "agent_id": command.agent_id,
            "schedule_type": command.schedule_type,
            "planned_at": command.planned_at.isoformat() if command.planned_at else None,
            "callback_url": command.callback_url,
            "dut": command.dut or {},
            "cases": [
                {"case_id": case_id, "auto_case_id": auto_case_id}
                for case_id, auto_case_id in zip(command.case_ids, command.auto_case_ids)
            ],
            "created_by": command.created_by,
        }

    @staticmethod
    def _extract_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 case 顺序。

        execution 的串行调度依赖稳定顺序，所以这里返回的是 payload 中记录的原始顺序，
        而不是重新排序后的集合。
        """
        return [case["case_id"] for case in payload.get("cases", [])]

    @staticmethod
    def _extract_auto_case_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
        """从任务快照中恢复 auto_case_id 顺序。"""
        return [case["auto_case_id"] for case in payload.get("cases", []) if "auto_case_id" in case]

    async def _resolve_task_case_pairs(self, task_doc: ExecutionTaskDoc) -> tuple[List[str], List[str]]:
        case_ids = self._extract_case_ids_from_payload(task_doc.request_payload)
        auto_case_ids = self._extract_auto_case_ids_from_payload(task_doc.request_payload)
        if not auto_case_ids:
            auto_case_ids = await self.resolve_auto_case_ids_by_case_ids(case_ids)
        return case_ids, auto_case_ids

    @staticmethod
    async def _create_task_run_docs(
            task_doc: ExecutionTaskDoc,
            trigger_type: str,
            triggered_by: str,
    ) -> None:
        """为当前任务创建一轮新的执行历史。

        这里的关键不是简单“插一条 run 记录”，而是把当前态整体快照成新的历史轮次：

        - `ExecutionTaskRunDoc` 记录任务级历史
        - `ExecutionTaskRunCaseDoc` 记录 case 级历史

        因此它通常出现在两类场景：

        - 任务初次创建后，预创建第 1 轮历史
        - 任务重试前，创建下一轮历史
        """
        run_no = task_doc.latest_run_no + 1
        task_doc.latest_run_no = run_no
        task_doc.current_run_no = run_no

        # 当前态 case 明细按顺序复制到 run_case 表，后续即使当前态被覆盖，
        # 历史轮次仍然能准确反映当时执行的 case 列表和顺序。
        case_docs = await (
            ExecutionTaskCaseDoc.find({"task_id": task_doc.task_id})
            .sort("order_no")
            .to_list()
        )
        await ExecutionTaskRunDoc(
            task_id=task_doc.task_id,
            run_no=run_no,
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            overall_status=task_doc.overall_status,
            dispatch_status=task_doc.dispatch_status,
            dispatch_channel=task_doc.dispatch_channel,
            case_count=task_doc.case_count,
            stop_mode=task_doc.stop_mode,
            stop_requested_at=task_doc.stop_requested_at,
            stop_requested_by=task_doc.stop_requested_by,
            stop_reason=task_doc.stop_reason,
        ).insert()
        for case_doc in case_docs:
            await ExecutionTaskRunCaseDoc(
                task_id=task_doc.task_id,
                run_no=run_no,
                case_id=case_doc.case_id,
                order_no=case_doc.order_no,
                case_snapshot=dict(case_doc.case_snapshot or {}),
                dispatch_status=case_doc.dispatch_status,
                dispatch_attempts=case_doc.dispatch_attempts,
                status=case_doc.status,
                progress_percent=case_doc.progress_percent,
                started_at=case_doc.started_at,
                finished_at=case_doc.finished_at,
                dispatched_at=case_doc.dispatched_at,
                last_seq=case_doc.last_seq,
                last_event_id=case_doc.last_event_id,
                result_data=dict(case_doc.result_data or {}),
            ).insert()

    @staticmethod
    async def _reset_task_case_docs(task_id: str) -> None:
        """重跑任务前重置当前态 case 明细。

        重试语义是“以同一个 task_id 再跑一轮”，不是新建任务。
        因此在保留 run 历史的前提下，需要把当前态 case 工作表清空回初始状态，
        让编排器像处理一轮全新执行那样继续工作。
        """
        case_docs = await ExecutionTaskCaseDoc.find({"task_id": task_id}).to_list()
        for case_doc in case_docs:
            ExecutionService._assign_fields(
                case_doc,
                dispatch_status="PENDING",
                dispatch_attempts=0,
                status="QUEUED",
                progress_percent=None,
                step_total=0,
                step_passed=0,
                step_failed=0,
                step_skipped=0,
                last_seq=0,
                last_event_id=None,
                started_at=None,
                finished_at=None,
                dispatched_at=None,
                result_data={},
            )
            await case_doc.save()

    @staticmethod
    def _build_case_snapshot(case_doc: TestCaseDoc, auto_case_id: str | None) -> Dict[str, Any]:
        """构建任务侧静态 case 快照。"""
        return {
            "case_id": case_doc.case_id,
            "auto_case_id": auto_case_id,
            "ref_req_id": case_doc.ref_req_id,
            "workflow_item_id": case_doc.workflow_item_id,
            "title": case_doc.title,
            "version": case_doc.version,
            "status": getattr(case_doc, "status", "draft"),
            "priority": case_doc.priority,
            "tags": list(case_doc.tags or []),
            "test_category": case_doc.test_category,
            "estimated_duration_sec": case_doc.estimated_duration_sec,
            "target_components": list(case_doc.target_components or []),
            "required_env": dict(case_doc.required_env or {}),
            "tooling_req": list(case_doc.tooling_req or []),
            "is_destructive": case_doc.is_destructive,
            "pre_condition": case_doc.pre_condition,
            "post_condition": case_doc.post_condition,
            "steps": [step.model_dump() for step in case_doc.steps],
            "cleanup_steps": [step.model_dump() for step in case_doc.cleanup_steps],
            "custom_fields": dict(case_doc.custom_fields or {}),
        }

    @staticmethod
    async def _delete_task_run_docs(task_id: str) -> None:
        """删除尚未真正执行前预创建的轮次历史。

        这个方法只用于“修改尚未触发的定时任务”场景。
        因为任务还没真正开始，旧的 run 快照不应该保留，否则会造成：

        - 当前态已经被新 case 列表替换
        - 历史态里却残留旧计划的第 1 轮快照

        这种历史对业务没有价值，反而会误导查询结果。
        """
        run_docs = await ExecutionTaskRunDoc.find({"task_id": task_id}).to_list()
        for run_doc in run_docs:
            await run_doc.delete()
        run_case_docs = await ExecutionTaskRunCaseDoc.find({"task_id": task_id}).to_list()
        for run_case_doc in run_case_docs:
            await run_case_doc.delete()

    @classmethod
    def _build_case_dispatch_command(
            cls,
            task_doc: ExecutionTaskDoc,
            case_ids: List[str],
            auto_case_ids: List[str],
            dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        """构建单 case 下发命令。"""
        request_payload = dict(task_doc.request_payload or {})
        planned_at = request_payload.get("planned_at")
        return DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
            framework=task_doc.framework,
            agent_id=task_doc.agent_id,
            trigger_source=request_payload.get("trigger_source", "manual"),
            created_by=task_doc.created_by,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            run_no=task_doc.current_run_no or 1,
            dispatch_case_id=case_ids[dispatch_case_index],
            dispatch_auto_case_id=auto_case_ids[dispatch_case_index],
            dispatch_case_index=dispatch_case_index,
            schedule_type=task_doc.schedule_type,
            planned_at=cls._ensure_utc_datetime(planned_at) if planned_at else None,
            callback_url=request_payload.get("callback_url"),
            dut=request_payload.get("dut"),
        )

    async def _build_task_dispatch_command(
            self,
            task_doc: ExecutionTaskDoc,
            dispatch_case_index: int,
    ) -> DispatchExecutionTaskCommand:
        case_ids, auto_case_ids = await self._resolve_task_case_pairs(task_doc)
        return self._build_case_dispatch_command(task_doc, case_ids, auto_case_ids, dispatch_case_index)

    @staticmethod
    async def _replace_task_case_docs(
            task_id: str,
            case_ids: List[str],
            auto_case_ids: List[str],
            doc_map: Dict[str, Any],
    ) -> None:
        """重建尚未触发任务的 case 明细快照。

        当前态 case 表本质上是一张“编排工作表”：

        - 保存顺序
        - 保存每条 case 的即时状态
        - 保存平台推进所需的游标信息

        当计划任务被修改时，直接整体重建比做增量 patch 更安全，能避免顺序、状态和
        历史残留字段之间出现不一致。
        """
        existing_docs = await ExecutionTaskCaseDoc.find({"task_id": task_id}).to_list()
        for existing_doc in existing_docs:
            await existing_doc.delete()

        auto_case_id_map = {
            case_id: auto_case_id
            for case_id, auto_case_id in zip(case_ids, auto_case_ids)
        }

        for order_no, case_id in enumerate(case_ids):
            case_doc = doc_map[case_id]
            snapshot = ExecutionService._build_case_snapshot(
                case_doc,
                auto_case_id=auto_case_id_map.get(case_id),
            )
            await ExecutionTaskCaseDoc(
                task_id=task_id,
                case_id=case_id,
                case_snapshot=snapshot,
                order_no=order_no,
                dispatch_status="PENDING",
                status="QUEUED",
                step_total=0,
                step_passed=0,
                step_failed=0,
                step_skipped=0,
                last_seq=0,
                result_data={},
            ).insert()

    @staticmethod
    def _ensure_pending_scheduled_task(task_doc: ExecutionTaskDoc) -> None:
        """限制取消/修改仅作用于未触发的定时任务。

        一旦任务已经触发，它就进入 execution 的实际编排阶段。此时再允许修改调度信息，
        会破坏当前态、run 历史以及外部执行端之间的一致性。
        """
        if task_doc.schedule_type != "SCHEDULED":
            raise ValueError(f"Task {task_doc.task_id} is not a scheduled task")
        if task_doc.schedule_status != "PENDING":
            raise ValueError(
                f"Task {task_doc.task_id} cannot be changed in schedule_status {task_doc.schedule_status}"
            )

    @staticmethod
    def _ensure_actor_identity(actual_actor_id: str, expected_actor_id: str) -> None:
        """校验操作者是否就是任务创建者。

        当前实现采用比较保守的约束：修改、取消、重试等敏感写操作要求操作者与
        `created_by` 一致。这里先做应用层兜底校验，避免只依赖接口层权限判断。
        """
        if actual_actor_id != expected_actor_id:
            logger.warning(f"Actor ID mismatch: actor={actual_actor_id}, expected={expected_actor_id}")
            raise ValueError("Actor identity mismatch")

    async def _ensure_no_active_duplicate(self, dedup_key: str, excluded_task_id: str | None = None) -> None:
        """阻止创建或修改为相同业务载荷的未完成任务。

        这里查询的是“未终态任务”。已经完成、失败、取消的旧任务不会阻塞新的创建；
        但仍在执行中的同义任务会被拦截，避免外部框架收到重复调度。
        """
        query: Dict[str, Any] = {
            "dedup_key": dedup_key,
            "overall_status": {"$nin": list(FINAL_TASK_STATUSES)},
            "is_deleted": False,
        }
        if excluded_task_id:
            query["task_id"] = {"$ne": excluded_task_id}

        pending_task = await ExecutionTaskDoc.find_one(query)
        if pending_task:
            raise ValueError(
                f"Task already exists and is not finished: existing_task_id={pending_task.task_id}"
            )

    @staticmethod
    def _apply_task_command_to_doc(
            task_doc: ExecutionTaskDoc,
            command: DispatchExecutionTaskCommand,
            dedup_key: str,
            schedule_type: str,
            schedule_status: str,
            dispatch_status: str,
    ) -> None:
        """把任务命令映射到任务文档，复用创建/修改路径。

        这个方法的目标是把“创建任务”和“更新未触发任务”两条路径统一起来，保证：

        - 相同字段有相同初始化逻辑
        - 状态重置完整，不遗留上一次执行痕迹
        - 当前态字段始终与 `request_payload` 对齐
        """
        ExecutionService._assign_fields(
            task_doc,
            agent_id=command.agent_id,
            dedup_key=dedup_key,
            case_count=len(command.case_ids),
            reported_case_count=0,
            current_case_id=command.case_ids[0],
            current_case_index=0,
            stop_mode=STOP_MODE_NONE,
            stop_requested_at=None,
            stop_requested_by=None,
            stop_reason=None,
            planned_at=command.planned_at,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status=dispatch_status,
            request_payload=ExecutionService._build_task_request_payload(command),
            dispatch_error=None,
            dispatch_response={},
            triggered_at=None,
            started_at=None,
            finished_at=None,
            last_callback_at=None,
            consume_status="PENDING",
            consumed_at=None,
            overall_status="QUEUED",
            orchestration_lock=None,
        )

    async def _dispatch_task_if_needed(
            self,
            task_doc: ExecutionTaskDoc,
            should_dispatch_now: bool,
            dispatch_case_index: int = 0,
    ) -> None:
        """按需下发指定索引的 case。"""
        if not should_dispatch_now:
            return
        await self._dispatch_existing_task(
            task_doc,
            await self._build_task_dispatch_command(task_doc, dispatch_case_index),
        )

    async def _dispatch_existing_task(
            self,
            task_doc: ExecutionTaskDoc,
            command: DispatchExecutionTaskCommand,
    ) -> None:
        """对已有任务执行真正下发。

        这里会同时更新三层数据：

        - 任务主表当前态
        - 当前 case 工作表
        - 当前 run 的历史快照

        这样无论调用方随后查询“任务当前状态”还是“本轮执行历史”，看到的结果都一致。
        """
        dispatch_result = await self._dispatcher.dispatch(command)
        case_doc = await ExecutionTaskCaseDoc.find_one({
            "task_id": task_doc.task_id,
            "case_id": command.dispatch_case_id,
        })
        # 任务主表记录的是“当前正在下发/已下发的 case”对应的全局状态。
        dispatch_time = datetime.now(timezone.utc)
        task_doc.dispatch_channel = dispatch_result.channel
        task_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
        task_doc.dispatch_error = dispatch_result.error
        task_doc.dispatch_response = dispatch_result.response
        # schedule_status 只表示调度是否已触发，不再混入下发成败语义。
        task_doc.schedule_status = "TRIGGERED"
        task_doc.current_case_id = command.dispatch_case_id
        task_doc.current_case_index = command.dispatch_case_index
        if not task_doc.triggered_at:
            task_doc.triggered_at = dispatch_time
        if dispatch_result.success:
            task_doc.overall_status = "QUEUED"
            task_doc.finished_at = None
        else:
            task_doc.overall_status = "FAILED"
            task_doc.finished_at = dispatch_time
        await task_doc.save()

        if case_doc:
            # case 当前态只反映这条 case 被下发了多少次、最后一次下发结果如何。
            case_doc.dispatch_attempts += 1
            case_doc.dispatch_status = "DISPATCHED" if dispatch_result.success else "DISPATCH_FAILED"
            case_doc.dispatched_at = dispatch_time
            await case_doc.save()

        if task_doc.current_run_no > 0:
            # 当前 run 同步一次任务级和 case 级快照，保证 run 视图可单独使用，
            # 不必再和当前态表进行拼装。
            run_doc = await ExecutionTaskRunDoc.find_one({
                "task_id": task_doc.task_id,
                "run_no": task_doc.current_run_no,
            })
            if run_doc:
                run_doc.dispatch_channel = dispatch_result.channel
                run_doc.dispatch_status = task_doc.dispatch_status
                run_doc.dispatch_response = dispatch_result.response
                run_doc.dispatch_error = dispatch_result.error
                await run_doc.save()
            if case_doc:
                run_case_doc = await ExecutionTaskRunCaseDoc.find_one({
                    "task_id": task_doc.task_id,
                    "run_no": task_doc.current_run_no,
                    "case_id": case_doc.case_id,
                })
                if run_case_doc:
                    run_case_doc.dispatch_attempts = case_doc.dispatch_attempts
                    run_case_doc.dispatch_status = case_doc.dispatch_status
                    run_case_doc.dispatched_at = case_doc.dispatched_at
                    await run_case_doc.save()

        if dispatch_result.success:
            logger.info(f"Successfully dispatched task {command.task_id} via {dispatch_result.channel}")
        else:
            logger.warning(f"Failed to dispatch task {command.task_id} via {dispatch_result.channel}")

    async def cancel_scheduled_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """取消未触发的定时任务。

        取消的前提是：

        - 任务存在
        - 操作者是任务创建者
        - 任务是 `SCHEDULED`
        - 且仍处于 `PENDING`
        """
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")
        self._ensure_actor_identity(actor_id, task_doc.created_by)

        self._ensure_pending_scheduled_task(task_doc)
        task_doc.schedule_status = "CANCELLED"
        task_doc.dispatch_status = "CANCELLED"
        task_doc.overall_status = "CANCELLED"
        await task_doc.save()

        return self._serialize_task_doc(task_doc)

    async def update_scheduled_task(
            self,
            task_id: str,
            actor_id: str,
            payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """修改未触发的定时任务。

        这条路径本质上是“保留 task_id 的前提下，重建任务当前态”。
        因为修改项可能覆盖 case 列表、计划时间、agent、回调地址和 DUT，
        所以这里不会做零碎字段 patch，而是：

        1. 重新装配命令对象
        2. 重新计算 dedup_key
        3. 覆盖任务主表
        4. 重建 case 当前态
        5. 清空旧的预创建 run 历史
        6. 重新创建第 1 轮 run
        7. 若已到触发时间，则立即下发首条 case
        """
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")
        self._ensure_actor_identity(actor_id, task_doc.created_by)

        self._ensure_pending_scheduled_task(task_doc)

        request_payload = dict(task_doc.request_payload or {})
        case_items = payload.get("cases")
        auto_case_ids = [item["auto_case_id"] for item in case_items] if case_items is not None else self._extract_auto_case_ids_from_payload(request_payload)
        if not auto_case_ids:
            case_ids = [item["case_id"] for item in case_items] if case_items is not None else [
                case["case_id"] for case in request_payload.get("cases", [])
            ]
            if not case_ids:
                raise ValueError("cases cannot be empty")
            auto_case_ids = await self.resolve_auto_case_ids_by_case_ids(case_ids)
        case_ids = await self.resolve_case_ids_by_auto_case_ids(auto_case_ids)
        if not case_ids:
            raise ValueError("cases cannot be empty")

        doc_map = await self._load_case_docs(case_ids)
        planned_at = payload.get("planned_at", task_doc.planned_at)
        agent_id = payload.get("agent_id", task_doc.agent_id)
        callback_url = payload.get("callback_url", request_payload.get("callback_url"))
        dut = payload.get("dut", request_payload.get("dut", {}))
        trigger_source = request_payload.get("trigger_source", "manual")

        schedule_type, normalized_planned_at, schedule_status, should_dispatch_now = self._normalize_schedule(
            task_doc.schedule_type,
            planned_at,
        )

        command = DispatchExecutionTaskCommand(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id or f"EXT-{task_doc.task_id}",
            framework=task_doc.framework,
            agent_id=agent_id,
            trigger_source=trigger_source,
            created_by=task_doc.created_by,
            auto_case_ids=auto_case_ids,
            case_ids=case_ids,
            schedule_type=schedule_type,
            planned_at=normalized_planned_at,
            callback_url=callback_url,
            dut=dut,
        )
        dedup_key = self._build_dedup_key(command)
        await self._ensure_no_active_duplicate(dedup_key, excluded_task_id=task_doc.task_id)

        self._apply_task_command_to_doc(
            task_doc=task_doc,
            command=command,
            dedup_key=dedup_key,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status="DISPATCHING" if should_dispatch_now else "PENDING",
        )
        await task_doc.save()
        await self._replace_task_case_docs(task_doc.task_id, case_ids, auto_case_ids, doc_map)
        await self._delete_task_run_docs(task_doc.task_id)
        # 计划任务在真正触发前的 run 历史是可重建的，因此这里把 run 序号复位后
        # 再创建新的首轮快照。
        task_doc.latest_run_no = 0
        task_doc.current_run_no = 0
        await self._create_task_run_docs(task_doc, trigger_type="INITIAL", triggered_by=actor_id)
        await task_doc.save()
        await self._dispatch_task_if_needed(task_doc, should_dispatch_now)

        return self._serialize_task_doc(task_doc)

    async def stop_task_after_current_case(
            self,
            task_id: str,
            actor_id: str,
            reason: str | None = None,
    ) -> Dict[str, Any]:
        """请求在当前 case 完成后停止任务，不再继续下发下一条。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        self._ensure_actor_identity(actor_id, task_doc.created_by)

        if task_doc.overall_status in FINAL_TASK_STATUSES:
            raise ValueError(f"Task {task_id} is already finished with status {task_doc.overall_status}")
        if task_doc.schedule_type == "SCHEDULED" and task_doc.schedule_status == "PENDING":
            raise ValueError(f"Task {task_id} has not started yet; use cancel instead")

        if task_doc.stop_mode == STOP_MODE_AFTER_CURRENT_CASE:
            return {
                "task_id": task_doc.task_id,
                "stop_mode": task_doc.stop_mode,
                "stop_requested_at": task_doc.stop_requested_at,
                "stop_requested_by": task_doc.stop_requested_by,
                "stop_reason": task_doc.stop_reason,
                "overall_status": task_doc.overall_status,
                "current_case_id": task_doc.current_case_id,
                "current_case_index": task_doc.current_case_index,
                "updated_at": task_doc.updated_at,
            }

        now = datetime.now(timezone.utc)
        task_doc.stop_mode = STOP_MODE_AFTER_CURRENT_CASE
        task_doc.stop_requested_at = now
        task_doc.stop_requested_by = actor_id
        task_doc.stop_reason = reason

        current_case_doc = None
        if task_doc.current_case_id:
            current_case_doc = await ExecutionTaskCaseDoc.find_one({
                "task_id": task_id,
                "case_id": task_doc.current_case_id,
            })

        if not current_case_doc or current_case_doc.status in FINAL_CASE_STATUSES:
            task_doc.overall_status = "STOPPED"
            task_doc.finished_at = now
            task_doc.last_callback_at = now
            task_doc.current_case_id = None
            task_doc.current_case_index = min(task_doc.current_case_index + 1, task_doc.case_count)
            if task_doc.dispatch_status != "DISPATCH_FAILED":
                task_doc.dispatch_status = "COMPLETED"

        await task_doc.save()
        await self._sync_run_from_task(task_doc)

        return {
            "task_id": task_doc.task_id,
            "stop_mode": task_doc.stop_mode,
            "stop_requested_at": task_doc.stop_requested_at,
            "stop_requested_by": task_doc.stop_requested_by,
            "stop_reason": task_doc.stop_reason,
            "overall_status": task_doc.overall_status,
            "current_case_id": task_doc.current_case_id,
            "current_case_index": task_doc.current_case_index,
            "updated_at": task_doc.updated_at,
        }

    async def dispatch_execution_task(
            self,
            command: DispatchExecutionTaskCommand,
            actor_id: str,
    ) -> Dict[str, Any]:
        """创建任务并启动首轮执行。

        这是 execution 模块最核心的入口之一。流程顺序不能随意调整：

        1. 校验操作者身份
        2. 校验 case 是否存在
        3. 归一化调度信息
        4. 做未完成任务去重
        5. 创建任务主表
        6. 创建 case 当前态工作表
        7. 预创建首轮 run 历史
        8. 如果需要，真实下发第 1 条 case
        """
        self._ensure_actor_identity(actor_id, command.created_by)
        doc_map = await self._load_case_docs(command.case_ids)
        schedule_type, planned_at, schedule_status, should_dispatch_now = self._normalize_schedule(
            command.schedule_type,
            command.planned_at,
        )
        command.schedule_type = schedule_type
        command.planned_at = planned_at
        dedup_key = self._build_dedup_key(command)
        await self._ensure_no_active_duplicate(dedup_key)

        task_doc = ExecutionTaskDoc(
            task_id=command.task_id,
            external_task_id=command.external_task_id,
            framework=command.framework,
            created_by=command.created_by,
            # 当前默认通过 dispatcher 走 Kafka 通道；后续如果支持更多通道，
            dispatch_channel="KAFKA",
        )
        self._apply_task_command_to_doc(
            task_doc=task_doc,
            command=command,
            dedup_key=dedup_key,
            schedule_type=schedule_type,
            schedule_status=schedule_status,
            dispatch_status="DISPATCHING" if should_dispatch_now else "PENDING",
        )
        await task_doc.insert()
        await self._replace_task_case_docs(task_doc.task_id, command.case_ids, command.auto_case_ids, doc_map)
        await self._create_task_run_docs(task_doc, trigger_type="INITIAL", triggered_by=actor_id)
        await task_doc.save()
        await self._dispatch_task_if_needed(task_doc, should_dispatch_now)
        return self._serialize_task_doc(task_doc)

    async def retry_failed_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """重新执行任务并保留历史轮次。

        这里的 retry 语义不是“只补跑失败 case”，而是“以同一个 task_id 重新跑一轮”。
        因此它会：

        - 重置当前态 case 表
        - 重置任务主表运行状态
        - 新增一个 `run_no`
        - 从第 1 条 case 重新开始下发
        """
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id, "is_deleted": False})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        self._ensure_actor_identity(actor_id, task_doc.created_by)

        if task_doc.schedule_type == "SCHEDULED" and task_doc.schedule_status == "PENDING":
            raise ValueError(f"Task {task_id} cannot be retried before scheduled trigger")

        case_ids, auto_case_ids = await self._resolve_task_case_pairs(task_doc)
        if not case_ids:
            raise ValueError(f"Task {task_id} has no cases to retry")

        await self._reset_task_case_docs(task_id)
        ExecutionService._assign_fields(
            task_doc,
            schedule_status="READY",
            dispatch_status="PENDING",
            dispatch_error=None,
            dispatch_response={},
            consume_status="PENDING",
            consumed_at=None,
            overall_status="QUEUED",
            reported_case_count=0,
            current_case_id=case_ids[0],
            current_case_index=0,
            stop_mode=STOP_MODE_NONE,
            stop_requested_at=None,
            stop_requested_by=None,
            stop_reason=None,
            triggered_at=None,
            started_at=None,
            finished_at=None,
            last_callback_at=None,
            orchestration_lock=None,
        )
        await self._create_task_run_docs(task_doc, trigger_type="RETRY", triggered_by=actor_id)
        await task_doc.save()

        await self._dispatch_existing_task(task_doc, await self._build_task_dispatch_command(task_doc, 0))

        if task_doc.dispatch_status == "DISPATCHED":
            logger.info(f"Task {task_id} retried successfully")
        else:
            logger.warning(f"Task {task_id} retry failed")

        return {
            "task_id": task_doc.task_id,
            "run_no": task_doc.current_run_no,
            "status": "retried" if task_doc.dispatch_status == "DISPATCHED" else "retry_failed",
            "message": task_doc.dispatch_response["message"],
        }

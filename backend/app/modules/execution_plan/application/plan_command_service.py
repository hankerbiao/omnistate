"""执行计划命令应用服务。

处理所有写操作（创建、更新、删除、派发、改派、结果回填等），
通过 Port 接口访问跨模块依赖（execution、notification）。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie.odm.operators.find.comparison import In as InOp

from app.modules.execution_plan.application.ports import (
    ExecutionDispatchPort,
    PlanNotificationPort,
)
from app.modules.execution_plan.domain.constants import PlanItemStatus
from app.modules.execution_plan.repository.models import (
    ExecutionPlanChangeLogDoc,
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
    ManualExecutionResultDoc,
)
from app.modules.execution_plan.schemas.execution_plan import DispatchConfig
from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService
from app.shared.core.logger import log as logger
from app.shared.service import SequenceIdService


class PlanCommandService:
    """执行计划写操作编排。

    职责：
    - 协调 ExecutionPlanService（核心 CRUD）与 Port 接口（跨模块副作用）
    - 所有写操作的入口，保证事务一致性（同一请求内的多个写操作）
    """

    def __init__(
        self,
        plan_service: ExecutionPlanService | None = None,
        dispatch_port: ExecutionDispatchPort | None = None,
        notification_port: PlanNotificationPort | None = None,
    ) -> None:
        from app.modules.execution_plan.application.adapters import (
            ExecutionDispatchAdapter,
            PlanNotificationAdapter,
        )
        self._plan_service = plan_service or ExecutionPlanService()
        self._dispatch_port = dispatch_port or ExecutionDispatchAdapter()
        self._notification_port = notification_port or PlanNotificationAdapter()

    # ─────────────────────────────────────────────────────────────────
    #  计划 CRUD（委托给核心服务）
    # ─────────────────────────────────────────────────────────────────

    async def create_plan(self, data: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
        return await self._plan_service.create_plan(data, actor_id)

    async def update_plan(self, plan_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._plan_service.update_plan(plan_id, data)

    async def delete_plan(self, plan_id: str) -> None:
        return await self._plan_service.delete_plan(plan_id)

    # ─────────────────────────────────────────────────────────────────
    #  计划条目管理
    # ─────────────────────────────────────────────────────────────────

    async def add_items(
        self,
        plan_id: str,
        items_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """添加条目到计划，并通知被指派人。"""
        await self._plan_service.get_plan_or_raise(plan_id)
        if not items_data:
            raise ValueError("items 不能为空")

        year = datetime.now().year
        seq_service = SequenceIdService()
        existing_count = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).count()

        # 收集 assignee 信息，创建完成后批量发送通知
        assignee_items: Dict[str, list[str]] = defaultdict(list)

        for idx, raw in enumerate(items_data):
            ref_type = str(raw.get("ref_type", "")).strip().lower()
            case_id = str(raw.get("case_id", "")).strip()
            if ref_type not in {"manual", "auto"}:
                raise ValueError(f"ref_type 无效: {ref_type}")
            if not case_id:
                raise ValueError("case_id 不能为空")

            snapshot = await self._plan_service.resolve_case_snapshot(ref_type, case_id)
            seq = await seq_service.next(f"execution_plan_item:{year}")
            item_id = f"EPI-{year}-{str(seq).zfill(6)}"
            order_no = raw.get("order_no")
            if order_no is None:
                order_no = existing_count + idx

            assignee_id = raw.get("assignee_id")
            case_title = snapshot.get("case_title", "")

            item_doc = ExecutionPlanItemDoc(
                item_id=item_id,
                plan_id=plan_id,
                ref_type=ref_type,
                case_id=case_id,
                manual_case_id=snapshot.get("manual_case_id"),
                case_title=case_title,
                component=str(raw.get("component") or snapshot.get("component") or ""),
                priority=snapshot.get("priority", ""),
                assignee_id=assignee_id,
                order_no=int(order_no),
            )
            await item_doc.insert()

            if assignee_id:
                assignee_items[assignee_id].append(case_title)

        await self._plan_service.recalculate_plan_progress(plan_id)

        # 通知被指派人（通过 Port）
        if assignee_items:
            plan_title = await self._plan_service.get_plan_title(plan_id)
            for user_id, titles in assignee_items.items():
                await self._notification_port.notify_assign(
                    user_id=user_id,
                    plan_title=plan_title,
                    case_titles=titles,
                )

        return await self._plan_service.get_plan(plan_id)

    async def delete_item(self, plan_id: str, item_id: str) -> None:
        """软删除计划条目。"""
        item = await self._plan_service.get_item_or_raise(plan_id, item_id)
        item.is_deleted = True
        await item.save()
        await self._plan_service.recalculate_plan_progress(plan_id)

    async def update_item(
        self,
        plan_id: str,
        item_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新计划条目字段，必要时记录审计日志。"""
        item = await self._plan_service.get_item_or_raise(plan_id, item_id)
        allowed = {"assignee_id", "status", "component", "order_no"}
        updates = self._plan_service._filter_updates(data, allowed)
        if "status" in updates:
            status_val = str(updates["status"])
            if status_val not in PlanItemStatus._value2member_map_:
                raise ValueError(f"status 无效: {status_val}, 可选: {[s.value for s in PlanItemStatus]}")
        self._plan_service._apply_updates(item, updates, allowed)
        await item.save()
        await self._plan_service.recalculate_plan_progress(plan_id)
        logger.debug("[ITEM] update_item plan={} item={} updates={}", plan_id, item_id, updates)
        if "assignee_id" in updates:
            await self._log_assignee_change(
                item=item, action="REASSIGN", operator_id="",
                old_value=data.get("_old_assignee_id"),
                new_value=updates["assignee_id"],
            )
        return await self._plan_service.item_to_response(item)

    async def reassign_item(
        self,
        item_id: str,
        assignee_id: str,
        operator_id: str,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        """改派计划条目执行人，记录审计日志并通知。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        old = item.assignee_id
        if old == assignee_id:
            return await self._plan_service.item_to_response(item)
        item.assignee_id = assignee_id
        await item.save()
        await self._log_assignee_change(
            item=item, action="REASSIGN", operator_id=operator_id,
            old_value=old, new_value=assignee_id, remark=remark,
        )
        logger.info("[REASSIGN] item={} {} -> {} by {}", item_id, old, assignee_id, operator_id)

        plan_title = await self._plan_service.get_plan_title(item.plan_id)
        await self._notification_port.notify_reassign(
            user_id=assignee_id,
            plan_title=plan_title,
            case_title=item.case_title,
        )

        return await self._plan_service.item_to_response(item)

    async def batch_update_assignee(
        self,
        plan_id: str,
        item_ids: List[str],
        assignee_id: Optional[str],
    ) -> Dict[str, Any]:
        """批量更新计划条目的执行人。"""
        await self._plan_service.get_plan_or_raise(plan_id)
        if not item_ids:
            raise ValueError("item_ids 不能为空")

        result = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            InOp(ExecutionPlanItemDoc.item_id, item_ids),
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).update({"$set": {"assignee_id": assignee_id, "updated_at": datetime.now(timezone.utc)}})

        await self._plan_service.recalculate_plan_progress(plan_id)
        updated = result.modified_count
        logger.debug("[ITEM] batch_update_assignee plan={} count={} assignee={}", plan_id, updated, assignee_id)

        if assignee_id and updated > 0:
            plan_title = await self._plan_service.get_plan_title(plan_id)
            await self._notification_port.notify_assign(
                user_id=assignee_id,
                plan_title=plan_title,
                case_titles=[f"（批量 {updated} 项）"],
            )

        return {
            "plan_id": plan_id,
            "updated_count": updated,
            "assignee_id": assignee_id,
        }

    # ─────────────────────────────────────────────────────────────────
    #  手工结果回填
    # ─────────────────────────────────────────────────────────────────

    async def submit_result(
        self,
        item_id: str,
        request: Any,
        actor_id: str,
    ) -> Dict[str, Any]:
        """提交手工测试结果回填。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        if item.ref_type != "manual":
            raise ValueError("仅手工条目支持结果回填")
        year = datetime.now().year
        seq = await SequenceIdService().next(f"manual_execution_result:{year}")
        result_id = f"MER-{year}-{str(seq).zfill(6)}"
        if item.result_id:
            existing = await ManualExecutionResultDoc.find_one(
                ManualExecutionResultDoc.result_id == item.result_id,
                ManualExecutionResultDoc.is_deleted == False,
            )
            if existing:
                existing.is_deleted = True
                await existing.save()
                logger.debug("[RESULT] replace previous result_id={}", item.result_id)
        result_doc = ManualExecutionResultDoc(
            result_id=result_id,
            item_id=item.item_id,
            plan_id=item.plan_id,
            case_id=item.manual_case_id or item.case_id,
            passed=request.passed,
            notes=request.notes,
            severity=request.severity,
            actual=request.actual,
            expected=request.expected,
            env=request.env,
            test_data=request.test_data,
            bug_id=request.bug_id,
            actual_duration=request.actual_duration,
            attachments=list(request.attachments),
            executed_by=actor_id,
            executed_at=request.executed_at or datetime.now(timezone.utc),
        )
        await result_doc.insert()
        item.result_id = result_id
        item.status = PlanItemStatus.DONE.value if request.passed else PlanItemStatus.FAIL.value
        await item.save()
        await self._plan_service.recalculate_plan_progress(item.plan_id)
        logger.info("[RESULT] submit_result item={} result={} passed={} actor={}", item_id, result_id, request.passed, actor_id)
        return self._plan_service.result_to_dict(result_doc)

    # ─────────────────────────────────────────────────────────────────
    #  自动化派发
    # ─────────────────────────────────────────────────────────────────

    async def dispatch_item(
        self,
        item_id: str,
        request: Any,
        actor_id: str,
    ) -> Dict[str, Any]:
        """派发单条自动化用例到执行引擎。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        if item.ref_type != "auto":
            raise ValueError("仅自动化条目支持计划内下发")
        if item.status != PlanItemStatus.PENDING.value:
            raise ValueError(f"仅 pending 状态的条目可下发，当前状态: {item.status}")

        data = await self._dispatch_port.dispatch_task(
            item_id=item.item_id,
            case_id=item.case_id,
            plan_id=item.plan_id,
            actor_id=actor_id,
            agent_id=request.agent_id,
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            category=request.category,
            project_tag=request.project_tag,
            repo_url=request.repo_url,
            branch=request.branch,
            pytest_options=dict(request.pytest_options),
            timeout=request.timeout,
            parameters=dict(request.parameters),
            config=dict(request.config),
        )
        task_id = data.get("task_id", "?")
        item.execution_task_id = task_id
        item.status = PlanItemStatus.RUNNING.value
        item.dispatch_config = DispatchConfig(
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            parameters=dict(request.parameters),
        )
        await item.save()
        await self._plan_service.recalculate_plan_progress(item.plan_id)
        logger.info("[DISPATCH] item={} task={} actor={}", item_id, task_id, actor_id)
        return data

    async def cancel_execution(
        self,
        item_id: str,
        actor_id: str,
    ) -> Dict[str, Any]:
        """取消计划条目的自动化执行。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        if item.ref_type != "auto":
            raise ValueError("仅自动化条目支持取消执行")
        if not item.execution_task_id:
            raise ValueError("该条目没有关联的执行任务，无需取消")

        await self._dispatch_port.cancel_task(item.execution_task_id)
        item.execution_task_id = None
        item.status = PlanItemStatus.PENDING.value
        await item.save()
        await self._plan_service.recalculate_plan_progress(item.plan_id)
        logger.info("[CANCEL] item={} status reset to pending, actor={}", item_id, actor_id)
        return await self._plan_service.item_to_response(item)

    async def rerun_item(
        self,
        item_id: str,
        request: Any,
        actor_id: str,
    ) -> Dict[str, Any]:
        """重新执行计划条目。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        if item.status not in (PlanItemStatus.FAIL.value, PlanItemStatus.DONE.value):
            raise ValueError(f"仅 fail/done 状态的条目支持重新执行，当前状态: {item.status}")

        if request.assignee_id is not None:
            item.assignee_id = request.assignee_id

        item.status = PlanItemStatus.PENDING.value
        if item.ref_type == "auto":
            item.execution_task_id = None
        await item.save()
        await self._plan_service.recalculate_plan_progress(item.plan_id)
        logger.info(
            "[RERUN] item={} ref_type={} status=reset->pending assignee={} actor={}",
            item_id, item.ref_type, request.assignee_id or "unchanged", actor_id,
        )

        if request.assignee_id is not None:
            plan_title = await self._plan_service.get_plan_title(item.plan_id)
            await self._notification_port.notify_rerun(
                user_id=request.assignee_id,
                plan_title=plan_title,
                case_title=item.case_title,
            )

        return await self._plan_service.item_to_response(item)

    async def batch_dispatch(
        self,
        request: Any,
        actor_id: str,
    ) -> List[Dict[str, Any]]:
        """批量派发自动化用例。"""
        if not request.item_ids:
            raise ValueError("item_ids 不能为空")
        results: List[Dict[str, Any]] = []
        for item_id in request.item_ids:
            from app.modules.execution_plan.schemas.execution_plan import PlanItemDispatchRequest
            item_dispatch = PlanItemDispatchRequest(
                agent_id=request.agent_id,
                schedule_type=request.schedule_type,
                planned_at=request.planned_at,
                category=request.category,
                project_tag=request.project_tag,
                pytest_options=request.pytest_options,
                timeout=request.timeout,
                parameters=dict(request.parameters),
            )
            data = await self.dispatch_item(
                item_id=item_id,
                request=item_dispatch,
                actor_id=actor_id,
            )
            results.append(data)
        return results

    # ─────────────────────────────────────────────────────────────────
    #  收纳箱（Archive）
    # ─────────────────────────────────────────────────────────────────

    async def archive_item(self, item_id: str, actor_id: str) -> None:
        """归档计划条目。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        if item.assignee_id and item.assignee_id != actor_id:
            if not await self._plan_service.is_admin_user(actor_id):
                raise ValueError("只能归档分配给自己的条目")
        item.archived_at = datetime.now(timezone.utc)
        await item.save()
        await self._plan_service.recalculate_plan_progress(item.plan_id)

    async def unarchive_item(self, item_id: str, actor_id: str) -> None:
        """取消归档计划条目。"""
        item = await self._plan_service.get_item_by_id_or_raise(item_id)
        if item.assignee_id and item.assignee_id != actor_id:
            if not await self._plan_service.is_admin_user(actor_id):
                raise ValueError("只能取消归档分配给自己的条目")
        item.archived_at = None
        await item.save()
        await self._plan_service.recalculate_plan_progress(item.plan_id)

    # ─────────────────────────────────────────────────────────────────
    #  内部辅助
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def _log_assignee_change(
        item: ExecutionPlanItemDoc,
        action: str,
        operator_id: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> None:
        """记录执行人变更审计日志。"""
        await ExecutionPlanChangeLogDoc(
            item_id=item.item_id,
            plan_id=item.plan_id,
            action=action,
            operator_id=operator_id,
            old_value=old_value,
            new_value=new_value,
            remark=remark,
        ).insert()

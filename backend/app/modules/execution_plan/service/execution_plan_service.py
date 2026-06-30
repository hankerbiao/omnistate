"""执行计划核心服务。

提供执行计划的 CRUD 操作、条目查询、统计聚合，以及供 application 层
调用的共享辅助方法。写操作中的跨模块编排（派发、通知、改派等）已
上移至 application/plan_command_service.py。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie.odm.operators.find.comparison import In as InOp

from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution_plan.domain.constants import PlanItemStatus, TASK_TO_ITEM_STATUS
from app.modules.execution_plan.domain.exceptions import (
    ItemNotFoundError,
    PlanNotFoundError,
    ResultNotFoundError,
)
from app.modules.execution_plan.repository.models import (
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
    ManualExecutionResultDoc,
)
from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc
from app.shared.service import BaseService, SequenceIdService
from app.shared.core.logger import log as logger

_TASK_STATUS_MAP = TASK_TO_ITEM_STATUS


class ExecutionPlanService(BaseService):
    """执行计划 CRUD 与查询。

    写操作中的跨模块编排（派发、通知、改派、结果回填等）
    由 application.PlanCommandService 负责。
    """

    # ─────────────────────────────────────────────────────────────────
    #  计划 CRUD
    # ─────────────────────────────────────────────────────────────────

    async def list_plans(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        filters = [ExecutionPlanDoc.is_deleted == False]
        if status:
            filters.append(ExecutionPlanDoc.status == status)
        docs = await ExecutionPlanDoc.find(*filters).sort("-updated_at").to_list()
        logger.debug("[CRUD] list_plans status={} count={}", status, len(docs))

        # 批量查询所有非删除条目，按 plan_id 分组，避免 N+1 查询
        plan_ids = [doc.plan_id for doc in docs]
        items_cursor = ExecutionPlanItemDoc.find(
            InOp(ExecutionPlanItemDoc.plan_id, list(plan_ids)),
            ExecutionPlanItemDoc.is_deleted == False,
        )
        items_by_plan: Dict[str, List[ExecutionPlanItemDoc]] = {}
        async for item in items_cursor:
            items_by_plan.setdefault(item.plan_id, []).append(item)

        results = []
        for doc in docs:
            plan_dict = self._plan_to_dict(doc)
            items = items_by_plan.get(doc.plan_id, [])
            item_count = len(items)
            done_count = sum(1 for i in items if i.status == "done")
            plan_dict["item_count"] = item_count
            plan_dict["done_count"] = done_count
            plan_dict["progress_percent"] = round(done_count / item_count * 100) if item_count else 0
            results.append(plan_dict)
        return results

    async def create_plan(self, data: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
        title = str(data.get("title", "")).strip()
        if not title:
            raise ValueError("计划标题不能为空")

        year = datetime.now().year
        seq_service = SequenceIdService()
        seq = await seq_service.next(f"execution_plan:{year}")
        plan_id = f"EP-{year}-{str(seq).zfill(6)}"

        doc = ExecutionPlanDoc(
            plan_id=plan_id,
            title=title,
            description=str(data.get("description") or ""),
            status=str(data.get("status") or "active"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            trigger_at=data.get("trigger_at"),
            created_by=actor_id,
        )
        await doc.insert()
        logger.info("[CRUD] create_plan plan_id={} title={} actor={}", plan_id, title, actor_id)
        return self._plan_to_dict(doc)

    async def get_plan(self, plan_id: str) -> Dict[str, Any]:
        plan_doc = await self.get_plan_or_raise(plan_id)
        items = await self._list_plan_items(plan_id)
        result = self._plan_to_dict(plan_doc)
        result["items"] = items
        return result

    async def update_plan(self, plan_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await self.get_plan_or_raise(plan_id)
        allowed = {"title", "description", "status", "start_date", "end_date", "trigger_at"}
        updates = self._filter_updates(data, allowed)
        if "title" in updates:
            title = str(updates["title"]).strip()
            if not title:
                raise ValueError("计划标题不能为空")
            updates["title"] = title
        self._apply_updates(doc, updates, allowed)
        await doc.save()
        return await self.get_plan(plan_id)

    async def delete_plan(self, plan_id: str) -> None:
        doc = await ExecutionPlanDoc.find_one(ExecutionPlanDoc.plan_id == plan_id)
        if not doc:
            raise PlanNotFoundError(plan_id)
        if doc.is_deleted:
            return  # 已是删除状态，幂等返回
        doc.is_deleted = True
        await doc.save()
        await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).update({"$set": {"is_deleted": True}})
        logger.info("[CRUD] delete_plan plan_id={}", plan_id)

    # ─────────────────────────────────────────────────────────────────
    #  条目查询
    # ─────────────────────────────────────────────────────────────────

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """获取单个计划条目详情。"""
        item = await self.get_item_by_id_or_raise(item_id)
        return await self.item_to_response(item)

    async def list_my_items(self, assignee_id: str) -> List[Dict[str, Any]]:
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.assignee_id == assignee_id,
            ExecutionPlanItemDoc.archived_at == None,  # noqa: E711
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).sort("-updated_at").to_list()
        plan_ids = {doc.plan_id for doc in docs}
        plan_map = await self._batch_load_plan_titles(plan_ids)
        results: List[Dict[str, Any]] = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
            except Exception as exc:
                logger.warning("[items] 同步条目状态失败 {}: {}", doc.item_id, exc)
            try:
                results.append(await self.item_to_response(doc, _plan_title=plan_map.get(doc.plan_id, "")))
            except Exception as exc:
                logger.warning("[items] 序列化条目失败 {}: {}", doc.item_id, exc)
                continue
        return results

    async def list_items(
        self,
        status: Optional[str] = None,
        plan_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """查询计划条目列表，支持按状态和计划ID过滤。"""
        filters: List[Any] = [
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ]
        if status:
            if status not in PlanItemStatus._value2member_map_:
                raise ValueError(f"status 无效: {status}, 可选: {[s.value for s in PlanItemStatus]}")
            filters.append(ExecutionPlanItemDoc.status == status)
        if plan_id:
            filters.append(ExecutionPlanItemDoc.plan_id == plan_id)

        docs = await ExecutionPlanItemDoc.find(
            *filters,
        ).sort("-updated_at").limit(limit).to_list()

        plan_ids = {doc.plan_id for doc in docs}
        plan_map = await self._batch_load_plan_titles(plan_ids)

        results: List[Dict[str, Any]] = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
                doc_dict = await self.item_to_response(doc, _plan_title=plan_map.get(doc.plan_id, ""))
                results.append(doc_dict)
            except Exception as exc:
                logger.warning("跳过异常计划条目 {}: {}", doc.item_id, exc)
                continue
        return results

    async def get_overview(self) -> Dict[str, Any]:
        """获取所有执行计划的运行总览（聚合统计 + 运行中的条目）。"""
        # 1. 一次查询获取所有未删除的计划
        plans = await ExecutionPlanDoc.find(
            ExecutionPlanDoc.is_deleted == False,  # noqa: E712
        ).sort("-updated_at").to_list()

        plan_id_to_doc: Dict[str, ExecutionPlanDoc] = {p.plan_id: p for p in plans}

        # 2. 一次查询获取所有未删除的条目
        all_items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).to_list()

        # 按 plan_id 分组
        items_by_plan: Dict[str, List[ExecutionPlanItemDoc]] = {}
        for item in all_items:
            items_by_plan.setdefault(item.plan_id, []).append(item)

        plan_summaries: List[Dict[str, Any]] = []
        total_items = 0
        running_items_total = 0
        pending_items_total = 0
        done_items_total = 0
        fail_items_total = 0

        for plan_doc in plans:
            items = items_by_plan.get(plan_doc.plan_id, [])
            running_count = sum(1 for i in items if i.status == "running")
            pending_count = sum(1 for i in items if i.status == "pending")
            done_count = sum(1 for i in items if i.status == "done")
            fail_count = sum(1 for i in items if i.status == "fail")
            item_count = len(items)

            total_items += item_count
            running_items_total += running_count
            pending_items_total += pending_count
            done_items_total += done_count
            fail_items_total += fail_count

            plan_summaries.append({
                "plan_id": plan_doc.plan_id,
                "title": plan_doc.title,
                "status": plan_doc.status,
                "progress_percent": plan_doc.progress_percent,
                "item_count": item_count,
                "running_count": running_count,
                "pending_count": pending_count,
                "done_count": done_count,
                "fail_count": fail_count,
            })

        # 3. 获取运行中的条目并同步状态
        running_items = [i for i in all_items if i.status == "running"]
        for item in running_items:
            if item.ref_type == "auto":
                await self._sync_auto_item_status(item)
        # 重新筛选（同步后可能不再是 running）
        running_items = [i for i in all_items if i.status == "running"]
        running_items.sort(key=lambda x: x.updated_at or datetime.min, reverse=True)

        running_items_data: List[Dict[str, Any]] = []
        for item in running_items:
            try:
                plan_doc = plan_id_to_doc.get(item.plan_id)
                plan_title = plan_doc.title if plan_doc else ""
                plan_status = plan_doc.status if plan_doc else ""
                item_data = await self.item_to_response(item, _plan_title=plan_title)
                item_data["plan_status"] = plan_status
                running_items_data.append(item_data)
            except Exception as exc:
                logger.warning("跳过异常计划条目 {}: {}", item.item_id, exc)
                continue

        return {
            "total_plans": len(plans),
            "total_items": total_items,
            "running_count": running_items_total,
            "pending_count": pending_items_total,
            "done_count": done_items_total,
            "fail_count": fail_items_total,
            "plans": plan_summaries,
            "running_items": running_items_data,
        }

    async def list_archived_items(self, assignee_id: str) -> List[Dict[str, Any]]:
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.assignee_id == assignee_id,
            ExecutionPlanItemDoc.archived_at != None,  # noqa: E711
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).sort("-archived_at").to_list()
        plan_ids = {doc.plan_id for doc in docs}
        plan_map = await self._batch_load_plan_titles(plan_ids)
        results: List[Dict[str, Any]] = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
            except Exception as exc:
                logger.warning("[items] 同步条目状态失败 {}: {}", doc.item_id, exc)
            try:
                results.append(await self.item_to_response(doc, _plan_title=plan_map.get(doc.plan_id, "")))
            except Exception as exc:
                logger.warning("[items] 序列化条目失败 {}: {}", doc.item_id, exc)
                continue
        return results

    # ─────────────────────────────────────────────────────────────────
    #  结果查询
    # ─────────────────────────────────────────────────────────────────

    async def get_result(self, item_id: str) -> Dict[str, Any]:
        item = await self.get_item_by_id_or_raise(item_id)
        if not item.result_id:
            raise ResultNotFoundError(item_id)
        result_doc = await ManualExecutionResultDoc.find_one(
            ManualExecutionResultDoc.result_id == item.result_id,
            ManualExecutionResultDoc.is_deleted == False,
        )
        if not result_doc:
            raise ResultNotFoundError(item_id)
        return self.result_to_dict(result_doc)

    async def get_case_execution_stats(self, case_id: str) -> Dict[str, Any]:
        """获取测试用例的执行统计（手工 + 自动化）。"""
        # 查询手工结果
        manual_results = await ManualExecutionResultDoc.find(
            ManualExecutionResultDoc.case_id == case_id,
            ManualExecutionResultDoc.is_deleted == False,
        ).sort("-executed_at").to_list()

        total = len(manual_results)
        passed = sum(1 for r in manual_results if r.passed)
        last_result = manual_results[0] if manual_results else None

        # 自动化执行统计
        auto_items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.case_id == case_id,
            ExecutionPlanItemDoc.ref_type == "auto",
            ExecutionPlanItemDoc.execution_task_id != None,
            ExecutionPlanItemDoc.is_deleted == False,
        ).to_list()

        task_ids = [it.execution_task_id for it in auto_items if it.execution_task_id]
        if task_ids:
            task_docs = await ExecutionTaskDoc.find(
                InOp(ExecutionTaskDoc.task_id, task_ids),
            ).to_list()
            _TASK_PASS_STATUS = {"PASSED", "DONE"}
            for t in task_docs:
                total += 1
                if t.overall_status in _TASK_PASS_STATUS:
                    passed += 1

        recent = []
        for r in manual_results[:10]:
            recent.append({
                "result_id": r.result_id,
                "passed": r.passed,
                "executed_by": r.executed_by,
                "executed_at": r.executed_at.isoformat(),
                "plan_id": r.plan_id,
                "notes": r.notes or "",
            })

        return {
            "case_id": case_id,
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            "last_executed_at": last_result.executed_at.isoformat() if last_result else None,
            "recent": recent,
        }

    # ─────────────────────────────────────────────────────────────────
    #  公开辅助方法（供 application 层调用，属于显式 API 契约）
    # ─────────────────────────────────────────────────────────────────

    async def _list_plan_items(self, plan_id: str) -> List[Dict[str, Any]]:
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,
        ).sort("+order_no").to_list()
        plan_title = await self.get_plan_title(plan_id)
        result = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
                result.append(await self.item_to_response(doc, _plan_title=plan_title))
            except Exception as e:
                logger.error("item_to_response 失败 (item_id={}): {}", doc.item_id, e, exc_info=True)
                continue
        return result

    async def item_to_response(
        self,
        item: ExecutionPlanItemDoc,
        _plan_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        if _plan_title is None:
            _plan_title = await self.get_plan_title(item.plan_id)
        result_payload = None
        if item.result_id:
            result_doc = await ManualExecutionResultDoc.find_one(
                ManualExecutionResultDoc.result_id == item.result_id,
                ManualExecutionResultDoc.is_deleted == False,
            )
            if result_doc:
                result_payload = self._result_payload(result_doc)
        return {
            "item_id": item.item_id,
            "plan_id": item.plan_id,
            "plan_title": _plan_title,
            "case_id": item.case_id,
            "case_title": item.case_title,
            "ref_type": item.ref_type,
            "component": item.component,
            "priority": item.priority,
            "assignee_id": item.assignee_id,
            "status": item.status,
            "order_no": item.order_no,
            "execution_task_id": item.execution_task_id,
            "result": result_payload,
            "archived_at": item.archived_at.isoformat() if item.archived_at else None,
            "dispatch_config": item.dispatch_config.model_dump() if item.dispatch_config else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

    async def _sync_auto_item_status(self, item: ExecutionPlanItemDoc) -> None:
        if item.ref_type != "auto" or not item.execution_task_id:
            return
        task_doc = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == item.execution_task_id,
            ExecutionTaskDoc.is_deleted == False,
        )
        if not task_doc:
            return
        mapped = _TASK_STATUS_MAP.get(task_doc.overall_status)
        if mapped and mapped != item.status:
            old_status = item.status
            item.status = mapped
            await item.save()
            await self.recalculate_plan_progress(item.plan_id)
            logger.debug(
                "[SYNC] item={} task={} status {} -> {} (task_overall={})",
                item.item_id, item.execution_task_id, old_status, mapped, task_doc.overall_status,
            )

    async def recalculate_plan_progress(self, plan_id: str) -> None:
        plan_doc = await self.get_plan_or_raise(plan_id)
        items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,
            ExecutionPlanItemDoc.archived_at == None,
        ).to_list()
        item_count = len(items)
        done_count = sum(1 for item in items if item.status == PlanItemStatus.DONE.value)
        fail_count = sum(1 for item in items if item.status == PlanItemStatus.FAIL.value)
        completed_count = done_count + fail_count
        progress = round(completed_count / item_count * 100) if item_count else 0
        plan_doc.item_count = item_count
        plan_doc.done_count = done_count
        plan_doc.progress_percent = progress
        if item_count > 0 and completed_count == item_count and plan_doc.status == "active":
            plan_doc.status = "done"
        await plan_doc.save()

    async def resolve_case_snapshot(self, ref_type: str, case_id: str) -> Dict[str, Any]:
        if ref_type == "manual":
            case_doc = await TestCaseDoc.find_one(
                TestCaseDoc.case_id == case_id,
                TestCaseDoc.is_deleted == False,
            )
            if not case_doc:
                raise ValueError(f"手工用例不存在: {case_id}")
            component = case_doc.lab_id or ""
            if case_doc.catalog_path:
                component = "/".join(case_doc.catalog_path[:2]) or component
            return {
                "case_title": case_doc.title,
                "component": component,
                "priority": case_doc.priority or "",
                "manual_case_id": case_doc.case_id,
            }
        auto_doc = await AutomationTestCaseDoc.find_one(
            AutomationTestCaseDoc.auto_case_id == case_id,
            AutomationTestCaseDoc.is_deleted == False,
        )
        if not auto_doc:
            raise ValueError(f"自动化用例不存在: {case_id}")
        manual_doc = await TestCaseDoc.find_one(
            TestCaseDoc.case_id == auto_doc.linked_manual_case_id,
            TestCaseDoc.is_deleted == False,
        )
        component = ""
        priority = ""
        if manual_doc:
            component = manual_doc.lab_id or ""
            if manual_doc.catalog_path:
                component = "/".join(manual_doc.catalog_path[:2]) or component
            priority = manual_doc.priority or ""
        return {
            "case_title": auto_doc.name,
            "component": component,
            "priority": priority,
            "manual_case_id": auto_doc.linked_manual_case_id,
        }

    async def get_plan_or_raise(self, plan_id: str) -> ExecutionPlanDoc:
        doc = await ExecutionPlanDoc.find_one(
            ExecutionPlanDoc.plan_id == plan_id,
            ExecutionPlanDoc.is_deleted == False,
        )
        if not doc:
            raise PlanNotFoundError(plan_id)
        return doc

    async def get_item_or_raise(self, plan_id: str, item_id: str) -> ExecutionPlanItemDoc:
        doc = await ExecutionPlanItemDoc.find_one(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.item_id == item_id,
            ExecutionPlanItemDoc.is_deleted == False,
        )
        if not doc:
            raise ItemNotFoundError(item_id)
        return doc

    async def get_item_by_id_or_raise(self, item_id: str) -> ExecutionPlanItemDoc:
        doc = await ExecutionPlanItemDoc.find_one(
            ExecutionPlanItemDoc.item_id == item_id,
            ExecutionPlanItemDoc.is_deleted == False,
        )
        if not doc:
            raise ItemNotFoundError(item_id)
        return doc

    @staticmethod
    async def is_admin_user(user_id: str) -> bool:
        """判断用户是否拥有 ADMIN 角色。"""
        from app.modules.auth.repository.models import UserDoc
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if not user:
            return False
        return any(
            rid.strip().upper().replace("ROLE_", "") == "ADMIN"
            for rid in (user.role_ids or [])
        )

    @staticmethod
    async def _batch_load_plan_titles(plan_ids: set[str]) -> Dict[str, str]:
        """批量加载 plan_id → plan_title 映射，避免 N+1 查询。"""
        if not plan_ids:
            return {}
        plan_docs = await ExecutionPlanDoc.find(
            InOp(ExecutionPlanDoc.plan_id, list(plan_ids)),
            ExecutionPlanDoc.is_deleted == False,
        ).to_list()
        return {p.plan_id: p.title for p in plan_docs}

    async def get_plan_title(self, plan_id: str) -> str:
        """查询单个 plan 的 title。"""
        plans = await self._batch_load_plan_titles({plan_id})
        return plans.get(plan_id, "")

    @staticmethod
    def _plan_to_dict(doc: ExecutionPlanDoc) -> Dict[str, Any]:
        return {
            "plan_id": doc.plan_id,
            "title": doc.title,
            "description": doc.description,
            "status": doc.status,
            "start_date": doc.start_date,
            "end_date": doc.end_date,
            "trigger_at": doc.trigger_at,
            "created_by": doc.created_by,
            "item_count": doc.item_count,
            "done_count": doc.done_count,
            "progress_percent": doc.progress_percent,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
        }

    @staticmethod
    def _result_payload(doc: ManualExecutionResultDoc) -> Dict[str, Any]:
        return {
            "passed": doc.passed,
            "notes": doc.notes,
            "severity": doc.severity,
            "actual": doc.actual,
            "expected": doc.expected,
            "env": doc.env,
            "test_data": doc.test_data,
            "bug_id": doc.bug_id,
            "actual_duration": doc.actual_duration,
            "attachments": list(doc.attachments),
            "executed_at": doc.executed_at,
        }

    def result_to_dict(self, doc: ManualExecutionResultDoc) -> Dict[str, Any]:
        data = self._result_payload(doc)
        data.update({
            "result_id": doc.result_id,
            "item_id": doc.item_id,
            "plan_id": doc.plan_id,
            "case_id": doc.case_id,
            "executed_by": doc.executed_by,
        })
        return data

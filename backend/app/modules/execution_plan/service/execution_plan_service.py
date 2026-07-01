"""执行计划核心服务。

提供执行计划的 CRUD 操作、条目查询、统计聚合，以及供 application 层
调用的共享辅助方法。写操作中的跨模块编排（派发、通知、改派等）已
上移至 application/plan_command_service.py。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie.odm.operators.find.comparison import In as InOp

from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution_plan.application.ports import (
    CaseSnapshot,
    CaseSnapshotResolverPort,
    UserQueryPort,
)
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
from app.shared.core.logger import log as logger
from app.shared.service import BaseService, SequenceIdService

_TASK_STATUS_MAP = TASK_TO_ITEM_STATUS


class ExecutionPlanService(BaseService):
    """执行计划 CRUD 与查询。

    写操作中的跨模块编排（派发、通知、改派、结果回填等）
    由 application.PlanCommandService 负责。
    """

    def __init__(
        self,
        case_snapshot_resolver: CaseSnapshotResolverPort | None = None,
        user_query: UserQueryPort | None = None,
    ) -> None:
        # 跨模块依赖通过端口注入；未注入时延迟加载默认实现（仅用于非 DI 场景）
        self._case_snapshot_resolver = case_snapshot_resolver
        self._user_query = user_query

    def _ensure_case_snapshot_resolver(self) -> CaseSnapshotResolverPort:
        if self._case_snapshot_resolver is None:
            from app.modules.test_specs.application.plan_case_snapshot_adapter import (
                PlanCaseSnapshotAdapter,
            )
            self._case_snapshot_resolver = PlanCaseSnapshotAdapter()
        return self._case_snapshot_resolver

    def _ensure_user_query(self) -> UserQueryPort:
        if self._user_query is None:
            from app.modules.auth.plan_user_query_adapter import PlanUserQueryAdapter
            self._user_query = PlanUserQueryAdapter()
        return self._user_query

    # ─────────────────────────────────────────────────────────────────
    #  计划 CRUD
    # ─────────────────────────────────────────────────────────────────

    async def list_plans(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """分页查询执行计划列表（含每计划的条目计数与进度）。

        只加载当前页计划对应的 items，避免全量加载。
        """
        filters = [ExecutionPlanDoc.is_deleted == False]  # noqa: E712
        if status:
            filters.append(ExecutionPlanDoc.status == status)

        total = await ExecutionPlanDoc.find(*filters).count()
        skip = (page - 1) * page_size
        docs = (
            await ExecutionPlanDoc.find(*filters)
            .sort("-updated_at")
            .skip(skip)
            .limit(page_size)
            .to_list()
        )
        logger.debug("[CRUD] list_plans status={} page={} page_size={} count={}", status, page, page_size, len(docs))

        # 只加载当前页 plan_ids 对应的条目，按 plan_id 分组，避免 N+1 查询
        plan_ids = [doc.plan_id for doc in docs]
        items_by_plan: Dict[str, List[ExecutionPlanItemDoc]] = {}
        if plan_ids:
            items_cursor = ExecutionPlanItemDoc.find(
                InOp(ExecutionPlanItemDoc.plan_id, plan_ids),
                ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
            )
            async for item in items_cursor:
                items_by_plan.setdefault(item.plan_id, []).append(item)

        results = []
        for doc in docs:
            plan_dict = self._plan_to_dict(doc)
            items = items_by_plan.get(doc.plan_id, [])
            item_count = len(items)
            done_count = sum(1 for i in items if i.status == PlanItemStatus.DONE)
            plan_dict["item_count"] = item_count
            plan_dict["done_count"] = done_count
            plan_dict["progress_percent"] = round(done_count / item_count * 100) if item_count else 0
            results.append(plan_dict)

        return {
            "items": results,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

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

    async def list_my_items(self, assignee_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """查询某人名下未归档的计划条目。"""
        return await self._list_items_by_assignee(assignee_id, archived=False, limit=limit)

    async def _list_items_by_assignee(
        self,
        assignee_id: str,
        archived: bool,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """按指派人查询条目，归档/未归档复用同一套加载与序列化逻辑。

        Args:
            assignee_id: 指派人 ID
            archived: True 查已归档条目（按归档时间倒序），False 查未归档（按更新时间倒序）
            limit: 返回条目数量上限，避免无限制全量加载
        """
        archived_filter = (
            ExecutionPlanItemDoc.archived_at != None  # noqa: E711
            if archived
            else ExecutionPlanItemDoc.archived_at == None  # noqa: E711
        )
        sort_field = "-archived_at" if archived else "-updated_at"
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.assignee_id == assignee_id,
            archived_filter,
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).sort(sort_field).limit(limit).to_list()
        plan_ids = {doc.plan_id for doc in docs}
        plan_map = await self._batch_load_plan_titles(plan_ids)
        # 批量加载 result（避免 N+1）
        result_ids = {doc.result_id for doc in docs if doc.result_id}
        result_map = await self._batch_load_results(result_ids)
        results: List[Dict[str, Any]] = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
            except Exception as exc:
                logger.warning("[items] 同步条目状态失败 {}: {}", doc.item_id, exc)
            try:
                results.append(await self.item_to_response(doc, _plan_title=plan_map.get(doc.plan_id, ""), result_map=result_map))
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
        # 批量加载 result（避免 N+1）
        result_ids = {doc.result_id for doc in docs if doc.result_id}
        result_map = await self._batch_load_results(result_ids)

        results: List[Dict[str, Any]] = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
                doc_dict = await self.item_to_response(doc, _plan_title=plan_map.get(doc.plan_id, ""), result_map=result_map)
                results.append(doc_dict)
            except Exception as exc:
                logger.warning("跳过异常计划条目 {}: {}", doc.item_id, exc)
                continue
        return results

    async def get_overview(self) -> Dict[str, Any]:
        """获取所有执行计划的运行总览（聚合统计 + 运行中的条目）。

        统计部分改用 aggregation pipeline 在 DB 端按 plan_id 分组，
        避免全量加载所有条目到内存（数据量大时 O(N×M) 内存与延迟）。
        """
        # 1. 查询所有未删除计划（基本信息，必须加载）
        plans = await ExecutionPlanDoc.find(
            ExecutionPlanDoc.is_deleted == False,  # noqa: E712
        ).sort("-updated_at").to_list()

        plan_id_to_doc: Dict[str, ExecutionPlanDoc] = {p.plan_id: p for p in plans}

        # 2. 用 aggregation 在 DB 端按 plan_id 分组统计各状态计数
        #    只返回 plan_id + 计数（远小于全量 items 文档）
        #    status 在 DB 中存储为字符串值（PlanItemStatus 继承 str）
        status_counts_pipeline = [
            {"$match": {"is_deleted": False}},
            {"$group": {
                "_id": "$plan_id",
                "item_count": {"$sum": 1},
                "running_count": {"$sum": {"$cond": [{"$eq": ["$status", PlanItemStatus.RUNNING.value]}, 1, 0]}},
                "pending_count": {"$sum": {"$cond": [{"$eq": ["$status", PlanItemStatus.PENDING.value]}, 1, 0]}},
                "done_count": {"$sum": {"$cond": [{"$eq": ["$status", PlanItemStatus.DONE.value]}, 1, 0]}},
                "fail_count": {"$sum": {"$cond": [{"$eq": ["$status", PlanItemStatus.FAIL.value]}, 1, 0]}},
            }},
        ]
        agg_results = await ExecutionPlanItemDoc.aggregate(status_counts_pipeline).to_list()
        stats_by_plan: Dict[str, Dict[str, Any]] = {r["_id"]: r for r in agg_results}

        plan_summaries: List[Dict[str, Any]] = []
        total_items = 0
        running_items_total = 0
        pending_items_total = 0
        done_items_total = 0
        fail_items_total = 0

        for plan_doc in plans:
            stats = stats_by_plan.get(plan_doc.plan_id, {})
            item_count = stats.get("item_count", 0)
            running_count = stats.get("running_count", 0)
            pending_count = stats.get("pending_count", 0)
            done_count = stats.get("done_count", 0)
            fail_count = stats.get("fail_count", 0)

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

        # 3. 只查询 running 状态的条目（而非全量 items 再内存过滤）
        running_items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
            ExecutionPlanItemDoc.status == PlanItemStatus.RUNNING,
        ).to_list()

        for item in running_items:
            if item.ref_type == "auto":
                try:
                    await self._sync_auto_item_status(item)
                except Exception as exc:
                    logger.warning("同步运行中条目状态失败 {}: {}", item.item_id, exc)

        # 重新查询 running（同步后部分条目可能已变为 done/fail）
        running_items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
            ExecutionPlanItemDoc.status == PlanItemStatus.RUNNING,
        ).sort("-updated_at").to_list()

        # 批量加载 running 条目的 result（避免 N+1）
        running_result_ids = {item.result_id for item in running_items if item.result_id}
        running_result_map = await self._batch_load_results(running_result_ids)

        running_items_data: List[Dict[str, Any]] = []
        for item in running_items:
            try:
                plan_doc = plan_id_to_doc.get(item.plan_id)
                plan_title = plan_doc.title if plan_doc else ""
                plan_status = plan_doc.status if plan_doc else ""
                item_data = await self.item_to_response(item, _plan_title=plan_title, result_map=running_result_map)
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

    async def list_archived_items(self, assignee_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """查询某人名下已归档的计划条目。"""
        return await self._list_items_by_assignee(assignee_id, archived=True, limit=limit)

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
        # 批量加载 result（避免 N+1）
        result_ids = {doc.result_id for doc in docs if doc.result_id}
        result_map = await self._batch_load_results(result_ids)
        result = []
        for doc in docs:
            try:
                await self._sync_auto_item_status(doc)
                result.append(await self.item_to_response(doc, _plan_title=plan_title, result_map=result_map))
            except Exception as e:
                logger.error("item_to_response 失败 (item_id={}): {}", doc.item_id, e, exc_info=True)
                continue
        return result

    async def item_to_response(
        self,
        item: ExecutionPlanItemDoc,
        _plan_title: Optional[str] = None,
        result_map: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if _plan_title is None:
            _plan_title = await self.get_plan_title(item.plan_id)
        result_payload = None
        if item.result_id:
            if result_map and item.result_id in result_map:
                result_payload = result_map[item.result_id]
            else:
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
        """通过端口解析用例快照，消除对 test_specs repository 的直接依赖。"""
        snapshot = await self._ensure_case_snapshot_resolver().resolve_case_snapshot(
            ref_type, case_id
        )
        return {
            "case_title": snapshot.case_title,
            "component": snapshot.component,
            "priority": snapshot.priority,
            "manual_case_id": snapshot.manual_case_id,
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

    async def is_admin_user(self, user_id: str) -> bool:
        """通过端口判断用户角色，消除对 auth repository 的直接依赖。"""
        return await self._ensure_user_query().is_admin(user_id)

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

    async def _batch_load_results(self, result_ids: set[str]) -> Dict[str, Any]:
        """批量加载手工执行结果，返回 {result_id: payload_dict} 映射"""
        if not result_ids:
            return {}
        docs = await ManualExecutionResultDoc.find(
            ManualExecutionResultDoc.result_id.is_in(list(result_ids)),
            ManualExecutionResultDoc.is_deleted == False,  # noqa: E712
        ).to_list()
        return {d.result_id: self._result_payload(d) for d in docs}

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

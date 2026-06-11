"""执行计划应用服务。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.execution.application.task_command_service import ExecutionTaskCommandService
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import DispatchCaseItem, DispatchTaskRequest
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
from app.modules.execution_plan.schemas.execution_plan import (
    BatchDispatchRequest,
    PlanItemDispatchRequest,
    SubmitManualResultRequest,
)
from app.modules.test_specs.repository.models import AutomationTestCaseDoc, TestCaseDoc
from app.shared.service import BaseService, SequenceIdService
from app.shared.core.logger import log as logger

_TASK_STATUS_MAP = {
    "QUEUED": "running",
    "RUNNING": "running",
    "PASSED": "done",
    "FAILED": "fail",
}


class ExecutionPlanService(BaseService):
    """执行计划 CRUD、条目管理、手工回填与计划内下发。"""

    def __init__(
        self,
        task_command_service: ExecutionTaskCommandService | None = None,
    ) -> None:
        self._task_command_service = task_command_service or ExecutionTaskCommandService()

    async def list_plans(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"is_deleted": False}
        if status:
            query["status"] = status
        docs = await ExecutionPlanDoc.find(query).sort("-updated_at").to_list()
        return [self._plan_to_dict(doc) for doc in docs]

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
            status=str(data.get("status") or "draft"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            trigger_at=data.get("trigger_at"),
            created_by=actor_id,
        )
        await doc.insert()
        return self._plan_to_dict(doc)

    async def get_plan(self, plan_id: str) -> Dict[str, Any]:
        plan_doc = await self._get_plan_or_raise(plan_id)
        items = await self._list_plan_items(plan_id)
        result = self._plan_to_dict(plan_doc)
        result["items"] = items
        return result

    async def update_plan(self, plan_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc = await self._get_plan_or_raise(plan_id)
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
        doc = await self._get_plan_or_raise(plan_id)
        doc.is_deleted = True
        await doc.save()
        await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).update({"$set": {"is_deleted": True}})

    async def add_items(
        self,
        plan_id: str,
        items_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        await self._get_plan_or_raise(plan_id)
        if not items_data:
            raise ValueError("items 不能为空")

        year = datetime.now().year
        seq_service = SequenceIdService()
        existing_count = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).count()

        for idx, raw in enumerate(items_data):
            ref_type = str(raw.get("ref_type", "")).strip().lower()
            case_id = str(raw.get("case_id", "")).strip()
            if ref_type not in {"manual", "auto"}:
                raise ValueError(f"ref_type 无效: {ref_type}")
            if not case_id:
                raise ValueError("case_id 不能为空")

            snapshot = await self._resolve_case_snapshot(ref_type, case_id)
            seq = await seq_service.next(f"execution_plan_item:{year}")
            item_id = f"EPI-{year}-{str(seq).zfill(6)}"
            order_no = raw.get("order_no")
            if order_no is None:
                order_no = existing_count + idx

            item_doc = ExecutionPlanItemDoc(
                item_id=item_id,
                plan_id=plan_id,
                ref_type=ref_type,
                case_id=case_id,
                manual_case_id=snapshot.get("manual_case_id"),
                case_title=snapshot.get("case_title", ""),
                component=str(raw.get("component") or snapshot.get("component") or ""),
                priority=snapshot.get("priority", ""),
                assignee_id=raw.get("assignee_id"),
                order_no=int(order_no),
            )
            await item_doc.insert()

        await self._recalculate_plan_progress(plan_id)
        return await self.get_plan(plan_id)

    async def update_item(
        self,
        plan_id: str,
        item_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        item = await self._get_item_or_raise(plan_id, item_id)
        allowed = {"assignee_id", "status", "component", "order_no"}
        updates = self._filter_updates(data, allowed)
        if "status" in updates:
            status = str(updates["status"])
            if status not in {"pending", "running", "done", "fail"}:
                raise ValueError(f"status 无效: {status}")
        self._apply_updates(item, updates, allowed)
        await item.save()
        await self._recalculate_plan_progress(plan_id)
        return await self._item_to_response(item)

    async def delete_item(self, plan_id: str, item_id: str) -> None:
        item = await self._get_item_or_raise(plan_id, item_id)
        item.is_deleted = True
        await item.save()
        await self._recalculate_plan_progress(plan_id)

    async def list_my_items(self, assignee_id: str) -> List[Dict[str, Any]]:
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.assignee_id == assignee_id,
            ExecutionPlanItemDoc.archived_at == None,  # noqa: E711
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).sort("-updated_at").to_list()
        results: List[Dict[str, Any]] = []
        for doc in docs:
            try:
                results.append(await self._item_to_response(doc))
            except Exception as exc:
                logger.warning(f"跳过异常计划条目 {doc.item_id}: {exc}")
                continue
        return results

    async def list_archived_items(self, assignee_id: str) -> List[Dict[str, Any]]:
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.assignee_id == assignee_id,
            ExecutionPlanItemDoc.archived_at != None,  # noqa: E711
            ExecutionPlanItemDoc.is_deleted == False,  # noqa: E712
        ).sort("-archived_at").to_list()
        return [await self._item_to_response(doc) for doc in docs]

    async def archive_item(self, item_id: str, actor_id: str) -> None:
        item = await self._get_item_by_id_or_raise(item_id)
        item.archived_at = datetime.now(timezone.utc)
        await item.save()
        await self._recalculate_plan_progress(item.plan_id)

    async def unarchive_item(self, item_id: str) -> None:
        item = await self._get_item_by_id_or_raise(item_id)
        item.archived_at = None
        await item.save()
        await self._recalculate_plan_progress(item.plan_id)

    async def submit_result(
        self,
        item_id: str,
        request: SubmitManualResultRequest,
        actor_id: str,
    ) -> Dict[str, Any]:
        item = await self._get_item_by_id_or_raise(item_id)
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
        item.status = "done" if request.passed else "fail"
        await item.save()
        await self._recalculate_plan_progress(item.plan_id)
        return self._result_to_dict(result_doc)

    async def get_result(self, item_id: str) -> Dict[str, Any]:
        item = await self._get_item_by_id_or_raise(item_id)
        if not item.result_id:
            raise ResultNotFoundError(item_id)
        result_doc = await ManualExecutionResultDoc.find_one(
            ManualExecutionResultDoc.result_id == item.result_id,
            ManualExecutionResultDoc.is_deleted == False,
        )
        if not result_doc:
            raise ResultNotFoundError(item_id)
        return self._result_to_dict(result_doc)

    async def get_case_execution_stats(self, case_id: str) -> Dict[str, Any]:
        """获取测试用例的执行统计（手工 + 自动化）。"""
        from beanie.odm.operators.find.comparison import In as InOp

        # 查询手工结果
        manual_results = await ManualExecutionResultDoc.find(
            ManualExecutionResultDoc.case_id == case_id,
            ManualExecutionResultDoc.is_deleted == False,
        ).sort("-executed_at").to_list()

        total = len(manual_results)
        passed = sum(1 for r in manual_results if r.passed)
        last_result = manual_results[0] if manual_results else None

        # 自动化执行统计：从计划条目关联的 task 状态获取
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
            _TASK_FAIL_STATUS = {"FAILED", "ERROR", "TIMEOUT"}
            for t in task_docs:
                total += 1
                if t.overall_status in _TASK_PASS_STATUS:
                    passed += 1

        # 最近 10 条记录
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

    async def dispatch_item(
        self,
        item_id: str,
        request: PlanItemDispatchRequest,
        actor_id: str,
        sequence_service: SequenceIdService,
    ) -> Dict[str, Any]:
        item = await self._get_item_by_id_or_raise(item_id)
        if item.ref_type != "auto":
            raise ValueError("仅自动化条目支持计划内下发")
        trigger_source = f"execution_plan:{item.plan_id}:{item.item_id}"
        category = request.category or f"{item.plan_id}/{item.item_id}"
        dispatch_request = DispatchTaskRequest(
            trigger_source=trigger_source,
            category=category,
            agent_id=request.agent_id,
            schedule_type=request.schedule_type,
            planned_at=request.planned_at,
            project_tag=request.project_tag,
            repo_url=request.repo_url,
            branch=request.branch,
            pytest_options=request.pytest_options,
            timeout=request.timeout,
            cases=[
                DispatchCaseItem(
                    auto_case_id=item.case_id,
                    parameters=dict(request.parameters),
                    config=dict(request.config),
                )
            ],
        )
        data = await self._task_command_service.create_and_dispatch_task(
            request=dispatch_request,
            actor_id=actor_id,
            sequence_service=sequence_service,
        )
        item.execution_task_id = data.get("task_id")
        item.status = "running"
        await item.save()
        await self._recalculate_plan_progress(item.plan_id)
        return data

    async def batch_dispatch(
        self,
        request: BatchDispatchRequest,
        actor_id: str,
        sequence_service: SequenceIdService,
    ) -> List[Dict[str, Any]]:
        if not request.item_ids:
            raise ValueError("item_ids 不能为空")
        results: List[Dict[str, Any]] = []
        for item_id in request.item_ids:
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
                sequence_service=sequence_service,
            )
            results.append(data)
        return results

    async def _list_plan_items(self, plan_id: str) -> List[Dict[str, Any]]:
        docs = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,
        ).sort("+order_no").to_list()
        result = []
        for doc in docs:
            try:
                result.append(await self._item_to_response(doc))
            except Exception as e:
                logger.error(f"_item_to_response 失败 (item_id={doc.item_id}): {e}", exc_info=True)
                raise
        return result

    async def _item_to_response(self, item: ExecutionPlanItemDoc) -> Dict[str, Any]:
        await self._sync_auto_item_status(item)
        plan_doc = await ExecutionPlanDoc.find_one(
            ExecutionPlanDoc.plan_id == item.plan_id,
            ExecutionPlanDoc.is_deleted == False,
        )
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
            "plan_title": plan_doc.title if plan_doc else "",
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
        }

    async def _sync_auto_item_status(self, item: ExecutionPlanItemDoc) -> None:
        if item.ref_type != "auto" or not item.execution_task_id:
            return
        if item.status in {"done", "fail"} and item.result_id:
            return
        task_doc = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == item.execution_task_id,
            ExecutionTaskDoc.is_deleted == False,
        )
        if not task_doc:
            return
        mapped = _TASK_STATUS_MAP.get(task_doc.overall_status)
        if mapped and mapped != item.status:
            item.status = mapped
            await item.save()
            await self._recalculate_plan_progress(item.plan_id)

    async def _recalculate_plan_progress(self, plan_id: str) -> None:
        plan_doc = await self._get_plan_or_raise(plan_id)
        items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,
        ).to_list()
        item_count = len(items)
        done_count = sum(1 for item in items if item.status == "done")
        progress = round(done_count / item_count * 100) if item_count else 0
        plan_doc.item_count = item_count
        plan_doc.done_count = done_count
        plan_doc.progress_percent = progress
        if item_count > 0 and done_count == item_count and plan_doc.status == "active":
            plan_doc.status = "done"
        await plan_doc.save()

    async def _resolve_case_snapshot(self, ref_type: str, case_id: str) -> Dict[str, Any]:
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
            TestCaseDoc.case_id == auto_doc.dml_manual_case_id,
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
            "manual_case_id": auto_doc.dml_manual_case_id,
        }

    async def _get_plan_or_raise(self, plan_id: str) -> ExecutionPlanDoc:
        doc = await ExecutionPlanDoc.find_one(
            ExecutionPlanDoc.plan_id == plan_id,
            ExecutionPlanDoc.is_deleted == False,
        )
        if not doc:
            raise PlanNotFoundError(plan_id)
        return doc

    async def _get_item_or_raise(self, plan_id: str, item_id: str) -> ExecutionPlanItemDoc:
        doc = await ExecutionPlanItemDoc.find_one(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.item_id == item_id,
            ExecutionPlanItemDoc.is_deleted == False,
        )
        if not doc:
            raise ItemNotFoundError(item_id)
        return doc

    async def _get_item_by_id_or_raise(self, item_id: str) -> ExecutionPlanItemDoc:
        doc = await ExecutionPlanItemDoc.find_one(
            ExecutionPlanItemDoc.item_id == item_id,
            ExecutionPlanItemDoc.is_deleted == False,
        )
        if not doc:
            raise ItemNotFoundError(item_id)
        return doc

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

    def _result_to_dict(self, doc: ManualExecutionResultDoc) -> Dict[str, Any]:
        data = self._result_payload(doc)
        data.update({
            "result_id": doc.result_id,
            "item_id": doc.item_id,
            "plan_id": doc.plan_id,
            "case_id": doc.case_id,
            "executed_by": doc.executed_by,
        })
        return data

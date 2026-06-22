"""项目服务层。"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.auth.repository.models import UserDoc
from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc
from app.modules.project.domain.constants import (
    PROJECT_ID_PREFIX,
    PROJECT_RELATED_MODEL_PATHS,
    ProjectStatus,
)
from app.modules.project.domain.exceptions import (
    ProjectKeyConflictError,
    ProjectNotFoundError,
)
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.schemas.project import (
    AssigneeDistribution,
    ExecutionTaskBreakdown,
    OwnerBrief,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectStatsResponse,
    StatsBreakdown,
)
from app.shared.core.logger import log as logger
from app.shared.service.base import BaseService


# ── 关联模型延迟加载 ──────────────────────────────────────────────────


def _get_related_models() -> list[type]:
    """延迟加载所有关联实体模型。"""
    models = []
    for module_path, class_name in PROJECT_RELATED_MODEL_PATHS:
        try:
            module = importlib.import_module(module_path)
            model_cls = getattr(module, class_name)
            models.append(model_cls)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to load related model {module_path}.{class_name}: {e}")
    return models


def _find_model(related: list[type], name: str) -> type:
    """在关联模型列表中按类名查找，未找到时抛出明确异常。"""
    for m in related:
        if m.__name__ == name:
            return m
    raise ValueError(
        f"Related model '{name}' is not registered in PROJECT_RELATED_MODEL_PATHS. "
        f"Available models: {[m.__name__ for m in related]}"
    )


# ── 辅助查询 ──────────────────────────────────────────────────────────


async def _resolve_owner(owner_id: Optional[str]) -> Optional[OwnerBrief]:
    if not owner_id:
        return None
    try:
        user = await UserDoc.find_one({"user_id": owner_id, "is_deleted": False})
        if user:
            return OwnerBrief(user_id=user.user_id, username=user.username)
    except Exception:
        pass
    return None


async def _fetch_assignee_distribution(project_id: str) -> List[AssigneeDistribution]:
    try:
        pipeline = [
            {"$match": {"project_ids": {"$in": [project_id]}, "is_deleted": False}},
            {"$group": {
                "_id": "$assignee_id",
                "item_count": {"$sum": 1},
                "done_count": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
            }},
            {"$sort": {"item_count": -1}},
        ]
        result = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
        return [
            AssigneeDistribution(
                assignee_id=r.get("_id"),
                assignee_name="",
                item_count=r.get("item_count", 0),
                done_count=r.get("done_count", 0),
                progress=round(r["done_count"] / r["item_count"] * 100, 1) if r.get("item_count") else 0.0,
            ) for r in result
        ]
    except Exception:
        return []


# ── 统计查询辅助函数 ──────────────────────────────────────────────────


def _make_project_filter(project_id: str, extra_filters: Optional[list] = None) -> dict:
    q: dict = {"project_ids": {"$in": [project_id]}, "is_deleted": False}
    if extra_filters:
        q["$and"] = list(extra_filters)
    return q


async def _count_for_project(model, project_id: str, extra_filters: Optional[list] = None) -> int:
    return await model.find(_make_project_filter(project_id, extra_filters)).count()


async def _compute_task_breakdown(task_cls, project_id: str) -> ExecutionTaskBreakdown:
    total = await _count_for_project(task_cls, project_id)
    done = await _count_for_project(task_cls, project_id, [{"overall_status": {"$in": ["FINISHED", "SUCCESS", "DONE"]}}])
    running = await _count_for_project(task_cls, project_id, [{"overall_status": {"$in": ["RUNNING", "DISPATCHED"]}}])
    failed = await _count_for_project(task_cls, project_id, [{"overall_status": {"$in": ["FAILED", "ERROR"]}}])
    pending = total - done - running - failed
    progress = round(done / total * 100, 1) if total > 0 else 0.0
    return ExecutionTaskBreakdown(
        total=total, done=done, running=running, failed=failed,
        pending=pending, progress=progress,
    )


async def _compute_pass_rates(project_id: str) -> tuple[StatsBreakdown, StatsBreakdown]:
    """使用 aggregation pipeline 分类型统计通过率，避免全量加载到内存。"""
    manual = StatsBreakdown()
    auto = StatsBreakdown()
    try:
        pipeline = [
            {"$match": {"project_ids": {"$in": [project_id]}, "is_deleted": False}},
            {"$group": {
                "_id": "$ref_type",
                "total": {"$sum": 1},
                "passed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
                "failed": {"$sum": {"$cond": [{"$eq": ["$status", "fail"]}, 1, 0]}},
            }},
        ]
        results = await ExecutionPlanItemDoc.aggregate(pipeline, projection_model=None).to_list()
        for r in results:
            ref_type = r.get("_id")
            total = r.get("total", 0)
            passed = r.get("passed", 0)
            failed = r.get("failed", 0)
            rate = round(passed / total * 100, 1) if total > 0 else 0.0
            sb = StatsBreakdown(total=total, passed=passed, failed=failed, pass_rate=rate)
            if ref_type == "manual":
                manual = sb
            elif ref_type == "auto":
                auto = sb
    except Exception:
        pass
    return manual, auto


async def _compute_coverage(test_case_count: int, requirement_count: int) -> float:
    return round(test_case_count / requirement_count * 100, 1) if requirement_count > 0 else 0.0


# ── 主服务类 ───────────────────────────────────────────────────────────


class ProjectService(BaseService):
    """项目 CRUD 与统计服务。"""

    # ── 响应构造 ──────────────────────────────────────────────────────

    @staticmethod
    async def _to_project_response(doc) -> ProjectResponse:
        owner = await _resolve_owner(doc.owner_id)
        return ProjectResponse(
            project_id=doc.project_id,
            key=doc.key,
            name=doc.name,
            description=doc.description,
            status=doc.status,
            priority=doc.priority,
            owner_id=doc.owner_id,
            owner=owner,
            start_date=doc.start_date,
            end_date=doc.end_date,
            target_version=doc.target_version,
            tags=doc.tags or [],
            created_by=doc.created_by,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    # ── 列表 ──────────────────────────────────────────────────────────

    @staticmethod
    async def list_projects(
        *,
        name: Optional[str] = None,
        status: Optional[str] = None,
        key: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        filters: list = [ProjectDoc.is_deleted == False]

        if name:
            filters.append(ProjectDoc.name == {"$regex": name, "$options": "i"})
        if status:
            filters.append(ProjectDoc.status == status)
        if key:
            filters.append(ProjectDoc.key == {"$regex": key, "$options": "i"})

        sort_field = getattr(ProjectDoc, sort_by, ProjectDoc.created_at)
        sort_direction = -1 if sort_order == "desc" else 1
        skip = (page - 1) * page_size

        total = await ProjectDoc.find({"$and": filters}).count()
        docs = await (
            ProjectDoc.find({"$and": filters})
            .sort((sort_field, sort_direction))
            .skip(skip)
            .limit(page_size)
            .to_list()
        )

        items = [await ProjectService._to_project_response(d) for d in docs]
        return {"items": items, "total": total}

    # ── 创建 ──────────────────────────────────────────────────────────

    @staticmethod
    async def create_project(
        data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> ProjectDoc:
        existing = await ProjectDoc.find_one(
            {"key": data["key"], "is_deleted": False}
        )
        if existing:
            raise ProjectKeyConflictError(data["key"])

        project_id = await ProjectService._generate_project_id()

        doc = ProjectDoc(
            project_id=project_id,
            key=data["key"],
            name=data["name"],
            description=data.get("description"),
            status=ProjectStatus.ACTIVE.value,
            priority=data.get("priority", "P2"),
            owner_id=data.get("owner_id"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            target_version=data.get("target_version"),
            tags=data.get("tags", []),
            created_by=created_by,
        )
        await doc.insert()
        logger.info(f"Project created: {project_id} ({data['key']})")
        return doc

    # ── 读取 ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_project(project_id: str) -> Optional[ProjectDoc]:
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")
        return doc

    @staticmethod
    async def get_project_detail(project_id: str) -> ProjectDetailResponse:
        doc = await ProjectService.get_project(project_id)
        stats = await ProjectService.get_project_stats(project_id)
        response = await ProjectService._to_project_response(doc)
        return ProjectDetailResponse(**response.model_dump(), stats=stats)

    # ── 更新 ──────────────────────────────────────────────────────────

    @staticmethod
    async def update_project(
        project_id: str,
        data: Dict[str, Any],
    ) -> ProjectDoc:
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        if "key" in data and data["key"] != doc.key:
            existing = await ProjectDoc.find_one(
                {"key": data["key"], "is_deleted": False, "project_id": {"$ne": project_id}}
            )
            if existing:
                raise ProjectKeyConflictError(data["key"])

        allowed_fields = {
            "name", "key", "description", "status",
            "priority", "owner_id", "start_date", "end_date",
            "target_version", "tags",
        }
        ProjectService._apply_updates(doc, data, allowed_fields)
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()
        logger.info(f"Project updated: {project_id}")
        return doc

    # ── 删除 ──────────────────────────────────────────────────────────

    @staticmethod
    async def delete_project(project_id: str) -> None:
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        doc.is_deleted = True
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()

        for model in _get_related_models():
            try:
                await model.find(
                    {"project_ids": project_id, "is_deleted": False}
                ).update_many({"$pull": {"project_ids": project_id}})
            except Exception as e:
                logger.warning(f"Failed to clean project_ids from {model.__name__}: {e}")

        logger.info(f"Project deleted: {project_id}")

    # ── 统计 ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_project_stats(project_id: str) -> ProjectStatsResponse:
        related = _get_related_models()

        tc = _find_model(related, "TestCaseDoc")
        ac = _find_model(related, "AutomationTestCaseDoc")
        rc = _find_model(related, "TestRequirementDoc")
        ec = _find_model(related, "TestCaseCollectionDoc")

        test_case_count = await _count_for_project(tc, project_id)
        auto_case_count = await _count_for_project(ac, project_id)
        requirement_count = await _count_for_project(rc, project_id)
        plan_count = await _count_for_project(_find_model(related, "ExecutionPlanDoc"), project_id)
        collection_count = await _count_for_project(ec, project_id)

        task = await _compute_task_breakdown(_find_model(related, "ExecutionTaskDoc"), project_id)
        manual_pass, auto_pass = await _compute_pass_rates(project_id)
        coverage_rate = await _compute_coverage(test_case_count, requirement_count)
        assignee_dist = await _fetch_assignee_distribution(project_id)

        return ProjectStatsResponse(
            test_case_count=test_case_count,
            auto_case_count=auto_case_count,
            requirement_count=requirement_count,
            plan_count=plan_count,
            collection_count=collection_count,
            task=task,
            task_progress=task.progress,
            manual_pass=manual_pass,
            auto_pass=auto_pass,
            coverage_rate=coverage_rate,
            assignee_distribution=assignee_dist,
        )

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    async def _generate_project_id() -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"{PROJECT_ID_PREFIX}-{year}-"
        last = await ProjectDoc.find(
            {"project_id": {"$regex": f"^{prefix}"}},
            sort=[("project_id", -1)],
        ).limit(1).to_list()
        seq = 1
        if last:
            seq = int(last[0].project_id.split("-")[-1]) + 1
        return f"{prefix}{seq:05d}"

"""项目服务层。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.project.domain.constants import PROJECT_RELATED_MODEL_PATHS, ProjectStatus
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
from app.shared.service.base import BaseService
from app.shared.core.logger import log as logger


def _get_related_models() -> list[type]:
    """延迟加载所有关联实体模型。"""
    models = []
    for module_path, class_name in PROJECT_RELATED_MODEL_PATHS:
        try:
            import importlib
            module = importlib.import_module(module_path)
            model_cls = getattr(module, class_name)
            models.append(model_cls)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to load related model {module_path}.{class_name}: {e}")
    return models


async def _resolve_owner(owner_id: Optional[str]) -> Optional[OwnerBrief]:
    """异步解析负责人信息。"""
    if not owner_id:
        return None
    try:
        from app.modules.auth.repository.models import UserDoc
        user = await UserDoc.find_one({"user_id": owner_id, "is_deleted": False})
        if user:
            return OwnerBrief(user_id=user.user_id, username=user.username)
    except Exception:
        pass
    return None


async def _get_plan_ids_for_project(project_id: str) -> List[str]:
    """获取项目关联的所有执行计划 ID（通过 ExecutionPlanDoc 关联）。"""
    try:
        from app.modules.execution_plan.repository.models import ExecutionPlanDoc
        plans = await ExecutionPlanDoc.find(
            {"project_ids": {"$in": [project_id]}, "is_deleted": False}
        ).to_list()
        return [p.plan_id for p in plans]
    except Exception:
        return []


async def _fetch_assignee_distribution(project_id: str) -> List[AssigneeDistribution]:
    """获取执行计划条目按执行人聚合的分布（通过 plan_ids 关联）。"""
    try:
        plan_ids = await _get_plan_ids_for_project(project_id)
        if not plan_ids:
            return []
        from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc
        pipeline = [
            {"$match": {"plan_id": {"$in": plan_ids}, "is_deleted": False}},
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
    except Exception as e:
        logger.warning(f"Failed to fetch assignee distribution: {e}")
        return []


class ProjectService(BaseService):
    """项目 CRUD 与统计服务。"""

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
        """获取项目列表（分页 + 搜索）。"""
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

        return {
            "items": items,
            "total": total,
        }

    # ── 创建 ──────────────────────────────────────────────────────────

    @staticmethod
    async def create_project(
        data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> ProjectDoc:
        """创建项目。"""
        existing = await ProjectDoc.find_one(
            {"key": data["key"], "is_deleted": False}
        )
        if existing:
            raise ValueError(f"项目标识已存在: {data['key']}")

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
        """获取项目文档。"""
        return await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )

    @staticmethod
    async def get_project_detail(project_id: str) -> Optional[ProjectDetailResponse]:
        """获取项目详情（含统计和负责人信息）。"""
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            return None

        stats = await ProjectService.get_project_stats(project_id)
        owner = await _resolve_owner(doc.owner_id)

        return ProjectDetailResponse(
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
            stats=stats,
        )

    # ── 更新 ──────────────────────────────────────────────────────────

    @staticmethod
    async def update_project(
        project_id: str,
        data: Dict[str, Any],
    ) -> ProjectDoc:
        """更新项目信息。"""
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ValueError(f"项目不存在: {project_id}")

        if "key" in data and data["key"] != doc.key:
            existing = await ProjectDoc.find_one(
                {"key": data["key"], "is_deleted": False, "project_id": {"$ne": project_id}}
            )
            if existing:
                raise ValueError(f"项目标识已存在: {data['key']}")

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
        """软删除项目，并清理所有关联实体的 project_ids。"""
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ValueError(f"项目不存在: {project_id}")

        doc.is_deleted = True
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()

        collections = _get_related_models()
        for model in collections:
            try:
                await model.find(
                    {"project_ids": project_id, "is_deleted": False}
                ).update_many({"$pull": {"project_ids": project_id}})
            except Exception as e:
                logger.warning(
                    f"Failed to clean project_ids from {model.__name__}: {e}"
                )

        logger.info(f"Project deleted: {project_id}, cleaned {len(collections)} collections")

    # ── 统计 ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_project_stats(project_id: str) -> ProjectStatsResponse:
        """获取项目下各类实体聚合统计。"""
        def _count(model, add_filters: Optional[list] = None):
            filters = [{"project_ids": {"$in": [project_id]}}, {"is_deleted": False}]
            if add_filters:
                filters.extend(add_filters)
            return model.find({"$and": filters}).count()

        related = _get_related_models()
        test_case_cls = next(m for m in related if m.__name__ == "TestCaseDoc")
        auto_case_cls = next(m for m in related if m.__name__ == "AutomationTestCaseDoc")
        req_cls = next(m for m in related if m.__name__ == "TestRequirementDoc")
        plan_cls = next(m for m in related if m.__name__ == "ExecutionPlanDoc")
        task_cls = next(m for m in related if m.__name__ == "ExecutionTaskDoc")
        collection_cls = next(m for m in related if m.__name__ == "TestCaseCollectionDoc")

        # 计数
        test_case_count = await _count(test_case_cls)
        auto_case_count = await _count(auto_case_cls)
        req_count = await _count(req_cls)
        plan_count = await _count(plan_cls)

        # 任务统计
        task_total = await _count(task_cls)
        task_done = await _count(task_cls, [{"overall_status": {"$in": ["FINISHED", "SUCCESS", "DONE"]}}])
        task_running = await _count(task_cls, [{"overall_status": {"$in": ["RUNNING", "DISPATCHED"]}}])
        task_failed = await _count(task_cls, [{"overall_status": {"$in": ["FAILED", "ERROR"]}}])
        task_pending = task_total - task_done - task_running - task_failed
        task_progress = round(task_done / task_total * 100, 1) if task_total > 0 else 0.0

        # 通过率 — 通过 plan_ids 关联查询 ExecutionPlanItemDoc
        manual_pass = StatsBreakdown()
        auto_pass = StatsBreakdown()
        try:
            plan_ids = await _get_plan_ids_for_project(project_id)
            if plan_ids:
                from app.modules.execution_plan.repository.models import ExecutionPlanItemDoc
                items = await ExecutionPlanItemDoc.find(
                    {"plan_id": {"$in": plan_ids}, "is_deleted": False}
                ).to_list()
                if items:
                    manual_items = [i for i in items if i.ref_type == "manual"]
                    auto_items = [i for i in items if i.ref_type == "auto"]
                    manual_pass = StatsBreakdown(
                        total=len(manual_items),
                        passed=sum(1 for i in manual_items if i.status == "done"),
                        failed=sum(1 for i in manual_items if i.status == "fail"),
                        pass_rate=round(sum(1 for i in manual_items if i.status == "done") / len(manual_items) * 100, 1) if manual_items else 0.0,
                    )
                    auto_pass = StatsBreakdown(
                        total=len(auto_items),
                        passed=sum(1 for i in auto_items if i.status == "done"),
                        failed=sum(1 for i in auto_items if i.status == "fail"),
                        pass_rate=round(sum(1 for i in auto_items if i.status == "done") / len(auto_items) * 100, 1) if auto_items else 0.0,
                    )
        except Exception as e:
            logger.warning(f"Failed to compute pass rate for project {project_id}: {e}")

        # 覆盖率
        coverage = round(test_case_count / req_count * 100, 1) if req_count > 0 else 0.0

        # 执行人分布
        assignee_dist = await _fetch_assignee_distribution(project_id)

        return ProjectStatsResponse(
            test_case_count=test_case_count,
            auto_case_count=auto_case_count,
            requirement_count=req_count,
            plan_count=plan_count,
            collection_count=await _count(collection_cls),
            task=ExecutionTaskBreakdown(
                total=task_total,
                done=task_done,
                running=task_running,
                failed=task_failed,
                pending=task_pending,
                progress=task_progress,
            ),
            task_progress=task_progress,
            manual_pass=manual_pass,
            auto_pass=auto_pass,
            coverage_rate=coverage,
            assignee_distribution=assignee_dist,
        )

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    async def _generate_project_id() -> str:
        """生成 project_id，格式: PRJ-YYYY-XXXXX。"""
        year = datetime.now(timezone.utc).year
        prefix = f"PRJ-{year}-"
        last = await ProjectDoc.find(
            {"project_id": {"$regex": f"^{prefix}"}},
            sort=[("project_id", -1)],
        ).limit(1).to_list()
        seq = 1
        if last:
            seq = int(last[0].project_id.split("-")[-1]) + 1
        return f"{prefix}{seq:05d}"

"""项目服务层。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.project.domain.constants import PROJECT_RELATED_MODEL_PATHS, ProjectStatus
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.schemas.project import (
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
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


class ProjectService(BaseService):
    """项目 CRUD 与统计服务。"""

    @staticmethod
    def _to_project_response(doc) -> ProjectResponse:
        return ProjectResponse(
            project_id=doc.project_id,
            key=doc.key,
            name=doc.name,
            description=doc.description,
            status=doc.status,
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

        # 排序
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

        items = [ProjectService._to_project_response(d) for d in docs]

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
        # 校验 key 唯一
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
            created_by=created_by,
        )
        await doc.insert()
        logger.info(f"Project created: {project_id} ({data['key']})")
        return doc

    # ── 读取 ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_project(project_id: str) -> Optional[ProjectDoc]:
        """获取项目详情。"""
        return await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )

    @staticmethod
    async def get_project_detail(project_id: str) -> Optional[ProjectDetailResponse]:
        """获取项目详情（含统计）。"""
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            return None

        stats = await ProjectService.get_project_stats(project_id)

        return ProjectDetailResponse(
            project_id=doc.project_id,
            key=doc.key,
            name=doc.name,
            description=doc.description,
            status=doc.status,
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
        """更新项目。"""
        doc = await ProjectDoc.find_one(
            {"project_id": project_id, "is_deleted": False}
        )
        if not doc:
            raise ValueError(f"项目不存在: {project_id}")

        # 如果修改 key，校验唯一性
        if "key" in data and data["key"] != doc.key:
            existing = await ProjectDoc.find_one(
                {"key": data["key"], "is_deleted": False, "project_id": {"$ne": project_id}}
            )
            if existing:
                raise ValueError(f"项目标识已存在: {data['key']}")

        allowed_fields = {"name", "key", "description", "status"}
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

        # 1. 软删除项目本身
        doc.is_deleted = True
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()

        # 2. 清理所有关联实体的 project_ids
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
        filters = [
            {"project_ids": {"$in": [project_id]}, "is_deleted": False},
        ]

        def _count_for_project(model, add_filters: Optional[list] = None):
            combined = list(filters)
            if add_filters:
                combined.extend(add_filters)
            return model.find({"$and": combined}).count()

        related = _get_related_models()
        test_case_cls = next(m for m in related if m.__name__ == "TestCaseDoc")
        auto_case_cls = next(m for m in related if m.__name__ == "AutomationTestCaseDoc")
        req_cls = next(m for m in related if m.__name__ == "TestRequirementDoc")
        plan_cls = next(m for m in related if m.__name__ == "ExecutionPlanDoc")
        task_cls = next(m for m in related if m.__name__ == "ExecutionTaskDoc")
        collection_cls = next(m for m in related if m.__name__ == "TestCaseCollectionDoc")

        test_case_count = await _count_for_project(test_case_cls)
        auto_case_count = await _count_for_project(auto_case_cls)
        requirement_count = await _count_for_project(req_cls)
        plan_count = await _count_for_project(plan_cls)
        task_count = await _count_for_project(task_cls)
        task_done_count = await _count_for_project(task_cls, [{"overall_status": {"$ne": "PENDING"}}])
        collection_count = await _count_for_project(collection_cls)

        task_progress = 0.0
        if task_count > 0:
            task_progress = round(task_done_count / task_count * 100, 1)

        return ProjectStatsResponse(
            test_case_count=test_case_count,
            auto_case_count=auto_case_count,
            requirement_count=requirement_count,
            plan_count=plan_count,
            task_count=task_count,
            task_done_count=task_done_count,
            task_progress=task_progress,
            collection_count=collection_count,
        )

    # ── 工具 ──────────────────────────────────────────────────────────

    @staticmethod
    async def _generate_project_id() -> str:
        """生成 project_id，格式: PRJ-YYYY-XXXXX。"""
        year = datetime.now(timezone.utc).year
        prefix = f"PRJ-{year}-"
        # 查询当年最大序号
        last = await ProjectDoc.find(
            {"project_id": {"$regex": f"^{prefix}"}},
            sort=[("project_id", -1)],
        ).limit(1).to_list()
        seq = 1
        if last:
            seq = int(last[0].project_id.split("-")[-1]) + 1
        return f"{prefix}{seq:05d}"

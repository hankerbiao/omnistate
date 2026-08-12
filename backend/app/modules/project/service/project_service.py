"""Project CRUD service and compatibility facade."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.project.domain.constants import PROJECT_ID_PREFIX, ProjectStatus
from app.modules.project.domain.exceptions import ProjectKeyConflictError, ProjectNotFoundError, ProjectQueryError
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.project.repository.models import ProjectMemberDoc
from app.modules.project.domain.constants import ProjectMemberRole
from app.modules.project.schemas.project import (
    BlockerItemResponse,
    GenerateDemoResponse,
    OwnerBrief,
    ProjectActivityResponse,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectStatsResponse,
)
from app.modules.project.service._related_models import get_related_models
from app.modules.project.service.project_dashboard_service import ProjectDashboardService
from app.modules.project.service.project_demo_service import ProjectDemoService
from app.shared.core.logger import log as logger
from app.shared.service.base import BaseService


class UserNameResolverPort(ABC):
    """Resolve a user ID without exposing auth details to callers."""

    @abstractmethod
    async def resolve_username(self, user_id: str) -> Optional[str]:
        ...


class _DefaultUserNameResolver(UserNameResolverPort):
    async def resolve_username(self, user_id: str) -> Optional[str]:
        try:
            from app.modules.auth.repository.models import UserDoc

            user = await UserDoc.find_one({"user_id": user_id})
            return user.username if user else None
        except Exception:
            return None


async def _resolve_owner(owner_id: Optional[str]) -> Optional[OwnerBrief]:
    if not owner_id:
        return None
    username = await _DefaultUserNameResolver().resolve_username(owner_id)
    return OwnerBrief(user_id=owner_id, username=username) if username else None


async def _batch_resolve_owners(owner_ids: set[str]) -> Dict[str, OwnerBrief]:
    if not owner_ids:
        return {}
    try:
        from app.modules.auth.repository.models import UserDoc

        users = await UserDoc.find({"user_id": {"$in": list(owner_ids)}}).to_list()
        return {
            user.user_id: OwnerBrief(user_id=user.user_id, username=user.username)
            for user in users
            if user.username
        }
    except Exception as exc:
        logger.warning("批量查询 owner 信息失败: {}", exc)
        return {}


class ProjectService(BaseService):
    """Project CRUD operations with stable facades for dashboard and demo features."""

    @staticmethod
    async def _to_project_response(
        doc,
        owner_map: Optional[Dict[str, OwnerBrief]] = None,
    ) -> ProjectResponse:
        owner = owner_map.get(doc.owner_id) if owner_map else await _resolve_owner(doc.owner_id)
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
        visible_project_ids: Optional[set[str]] = None,
    ) -> Dict[str, Any]:
        filters: list = [ProjectDoc.is_deleted == False]  # noqa: E712
        if visible_project_ids is not None:
            filters.append({"project_id": {"$in": list(visible_project_ids)}})
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

        owner_ids = {doc.owner_id for doc in docs if doc.owner_id}
        owner_map = await _batch_resolve_owners(owner_ids)
        items = [await ProjectService._to_project_response(doc, owner_map) for doc in docs]
        return {"items": items, "total": total}

    @staticmethod
    async def create_project(
        data: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> ProjectDoc:
        if data.get("priority", "P2") not in {"P0", "P1", "P2"}:
            raise ProjectQueryError("优先级必须为 P0、P1 或 P2")
        if data.get("start_date") and data.get("end_date") and data["start_date"] > data["end_date"]:
            raise ProjectQueryError("项目开始时间不能晚于结束时间")
        if data.get("owner_id"):
            from app.modules.auth.repository.models import UserDoc
            owner = await UserDoc.find_one({"user_id": data["owner_id"], "status": "ACTIVE"})
            if not owner:
                raise ProjectQueryError("项目负责人不存在或已停用")
        existing = await ProjectDoc.find_one({"key": data["key"], "is_deleted": False})
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
        if created_by:
            # Project creator owns the initial project-level administration scope.
            try:
                await ProjectMemberDoc(
                    project_id=project_id,
                    user_id=created_by,
                    role_code=ProjectMemberRole.PROJECT_ADMIN.value,
                ).insert()
            except Exception:
                doc.is_deleted = True
                doc.updated_at = datetime.now(timezone.utc)
                await doc.save()
                raise
        logger.info("Project created: {} ({})", project_id, data["key"])
        return doc

    @staticmethod
    async def get_project(project_id: str) -> ProjectDoc:
        doc = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")
        return doc

    @staticmethod
    async def get_project_detail(project_id: str) -> ProjectDetailResponse:
        doc = await ProjectService.get_project(project_id)
        stats = await ProjectService.get_project_stats(project_id)
        response = await ProjectService._to_project_response(doc)
        return ProjectDetailResponse(**response.model_dump(), stats=stats)

    @staticmethod
    async def update_project(project_id: str, data: Dict[str, Any]) -> ProjectDoc:
        doc = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")
        if doc.status == ProjectStatus.ARCHIVED.value and data.get("status") != ProjectStatus.ACTIVE.value:
            raise ProjectQueryError("归档项目为只读，只允许恢复为 active")
        if "status" in data and data["status"] not in {item.value for item in ProjectStatus}:
            raise ProjectQueryError("无效的项目状态")
        if "priority" in data and data["priority"] not in {"P0", "P1", "P2"}:
            raise ProjectQueryError("优先级必须为 P0、P1 或 P2")
        start_date = data.get("start_date", doc.start_date)
        end_date = data.get("end_date", doc.end_date)
        if start_date and end_date and start_date > end_date:
            raise ProjectQueryError("项目开始时间不能晚于结束时间")

        if "key" in data and data["key"] != doc.key:
            existing = await ProjectDoc.find_one({
                "key": data["key"],
                "is_deleted": False,
                "project_id": {"$ne": project_id},
            })
            if existing:
                raise ProjectKeyConflictError(data["key"])

        allowed_fields = {
            "name", "key", "description", "status", "priority", "owner_id",
            "start_date", "end_date", "target_version", "tags",
        }
        ProjectService._apply_updates(doc, data, allowed_fields)
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()
        logger.info("Project updated: {}", project_id)
        return doc

    @staticmethod
    async def delete_project(project_id: str) -> None:
        doc = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
        if not doc:
            raise ProjectNotFoundError(f"项目不存在: {project_id}")

        doc.is_deleted = True
        doc.updated_at = datetime.now(timezone.utc)
        await doc.save()
        # Keep project membership and asset metadata out of normal queries after a project is removed.
        for model_name in (
            ProjectMemberDoc,
        ):
            await model_name.find({"project_id": project_id, "is_deleted": False}).update_many({"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}})
        try:
            from app.modules.project.repository.models import (
                ProjectDocumentDoc, ProjectDocumentVersionDoc, ProjectFileDoc, ProjectFolderDoc,
            )
            for model in (ProjectDocumentDoc, ProjectDocumentVersionDoc, ProjectFolderDoc, ProjectFileDoc):
                await model.find({"project_id": project_id, "is_deleted": False}).update_many({"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}})
        except Exception as exc:
            logger.warning("Failed to clean project assets for {}: {}", project_id, exc)
        for model in get_related_models():
            try:
                await model.find({
                    "project_ids": project_id,
                    "is_deleted": False,
                }).update_many({"$pull": {"project_ids": project_id}})
            except Exception as exc:
                logger.warning("Failed to clean project_ids from {}: {}", model.__name__, exc)
        logger.info("Project deleted: {}", project_id)

    @staticmethod
    async def get_project_stats(project_id: str) -> ProjectStatsResponse:
        return await ProjectDashboardService.get_project_stats(project_id)

    @staticmethod
    async def get_blockers(project_id: str) -> List[BlockerItemResponse]:
        return await ProjectDashboardService.get_blockers(project_id)

    @staticmethod
    async def get_activities(
        project_id: str,
        limit: int = ProjectDashboardService.DEFAULT_ACTIVITY_LIMIT,
    ) -> List[ProjectActivityResponse]:
        return await ProjectDashboardService.get_activities(project_id, limit=limit)

    @staticmethod
    async def generate_demo_data(project_id: str) -> GenerateDemoResponse:
        return await ProjectDemoService.generate(project_id)

    @staticmethod
    async def _generate_project_id() -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"{PROJECT_ID_PREFIX}-{year}-"
        last = await ProjectDoc.find(
            {"project_id": {"$regex": f"^{prefix}"}},
            sort=[("project_id", -1)],
        ).limit(1).to_list()
        seq = int(last[0].project_id.split("-")[-1]) + 1 if last else 1
        return f"{prefix}{seq:05d}"

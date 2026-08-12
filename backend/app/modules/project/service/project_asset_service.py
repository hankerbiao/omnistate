"""Project-scoped membership, controlled document, and file-library services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from app.modules.attachments.service import AttachmentService
from app.modules.project.domain.constants import (
    ProjectDocumentStatus, ProjectMemberRole, ProjectReviewDecision,
)
from app.modules.project.domain.exceptions import (
    ProjectAssetNotFoundError, ProjectPermissionError, ProjectQueryError,
)
from app.modules.project.repository.models import (
    DocumentReviewer, ProjectDocumentDoc, ProjectDocumentVersionDoc, ProjectFileDoc,
    ProjectFolderDoc, ProjectMemberDoc,
)

PHASE_CODES = frozenset({"ECT", "DVT", "PVT"})
ROLE_ORDER = {
    ProjectMemberRole.PROJECT_ADMIN.value: 4,
    ProjectMemberRole.PROJECT_MAINTAINER.value: 3,
    ProjectMemberRole.PROJECT_REVIEWER.value: 2,
    ProjectMemberRole.PROJECT_VIEWER.value: 1,
}
REVIEWER_ROLES = frozenset({
    ProjectMemberRole.PROJECT_ADMIN.value,
    ProjectMemberRole.PROJECT_REVIEWER.value,
})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_name(value: str) -> tuple[str, str]:
    name = (value or "").strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ProjectQueryError("名称不能为空且不能包含路径分隔符")
    return name, name.casefold()


class ProjectAssetService:
    @staticmethod
    async def get_member(project_id: str, user_id: str) -> ProjectMemberDoc | None:
        return await ProjectMemberDoc.find_one({"project_id": project_id, "user_id": user_id, "is_deleted": False})

    @classmethod
    async def require_role(cls, project_id: str, user_id: str, roles: Iterable[str]) -> ProjectMemberDoc:
        member = await cls.get_member(project_id, user_id)
        if not member or member.role_code not in set(roles):
            raise ProjectPermissionError("用户不是项目成员或没有执行该操作的项目权限")
        return member

    @staticmethod
    async def list_members(project_id: str) -> list[ProjectMemberDoc]:
        return await ProjectMemberDoc.find({"project_id": project_id, "is_deleted": False}).sort("joined_at").to_list()

    @staticmethod
    async def list_members_for_user(user_id: str) -> list[ProjectMemberDoc]:
        return await ProjectMemberDoc.find({"user_id": user_id, "is_deleted": False}).to_list()

    @classmethod
    async def upsert_member(cls, project_id: str, user_id: str, role_code: str) -> ProjectMemberDoc:
        if role_code not in ROLE_ORDER:
            raise ProjectQueryError("无效的项目角色")
        from app.modules.auth.repository.models import UserDoc
        user = await UserDoc.find_one({"user_id": user_id, "status": "ACTIVE"})
        if not user:
            raise ProjectQueryError("用户不存在或已停用")
        member = await cls.get_member(project_id, user_id)
        if member:
            member.role_code = role_code
            member.updated_at = _now()
            await member.save()
            return member
        member = ProjectMemberDoc(project_id=project_id, user_id=user_id, role_code=role_code, joined_at=_now())
        await member.insert()
        return member

    @classmethod
    async def remove_member(cls, project_id: str, user_id: str) -> None:
        member = await cls.get_member(project_id, user_id)
        if not member:
            raise ProjectAssetNotFoundError("项目成员不存在")
        if member.role_code == ProjectMemberRole.PROJECT_ADMIN.value:
            admins = await ProjectMemberDoc.find({"project_id": project_id, "role_code": member.role_code, "is_deleted": False}).count()
            if admins <= 1:
                raise ProjectQueryError("项目必须至少保留一名项目管理员")
        member.is_deleted = True
        member.updated_at = _now()
        await member.save()

    @staticmethod
    def _validate_phase(phase_code: str) -> str:
        phase = (phase_code or "").strip().upper()
        if phase not in PHASE_CODES:
            raise ProjectQueryError("当前阶段必须为 ECT、DVT 或 PVT")
        return phase

    @staticmethod
    def _version_dict(doc: ProjectDocumentVersionDoc) -> dict[str, Any]:
        return {
            "document_id": doc.document_id, "project_id": doc.project_id, "version": doc.version,
            "phase_code": doc.phase_code, "attachment_id": doc.attachment_id,
            "submitted_by": doc.submitted_by, "reviewers": [item.model_dump() for item in doc.reviewers],
            "status": doc.status, "submitted_at": doc.submitted_at, "completed_at": doc.completed_at,
        }

    @staticmethod
    def _document_dict(doc: ProjectDocumentDoc) -> dict[str, Any]:
        return {
            "document_id": doc.document_id, "project_id": doc.project_id, "name": doc.name,
            "current_version": doc.current_version, "phase_code": doc.phase_code,
            "status": doc.status, "updated_by": doc.updated_by, "updated_at": doc.updated_at,
        }

    @classmethod
    async def create_document(cls, project_id: str, name: str, phase_code: str, attachment_id: str, updated_by: str, reviewer_ids: list[str]) -> dict[str, Any]:
        name, _ = _clean_name(name)
        phase = cls._validate_phase(phase_code)
        if not reviewer_ids or len(set(reviewer_ids)) != len(reviewer_ids):
            raise ProjectQueryError("至少指定一名不重复的审核人")
        members = {member.user_id: member for member in await cls.list_members(project_id)}
        if any(user_id not in members for user_id in reviewer_ids):
            raise ProjectQueryError("审核人必须是项目成员")
        if any(members[user_id].role_code not in REVIEWER_ROLES for user_id in reviewer_ids):
            raise ProjectQueryError("审核人必须拥有 PROJECT_REVIEWER 或 PROJECT_ADMIN 角色")
        document_id = str(uuid.uuid4())
        now = _now()
        if await ProjectDocumentDoc.find_one({"project_id": project_id, "name": name, "is_deleted": False}):
            raise ProjectQueryError("项目中已存在同名文档")
        document = ProjectDocumentDoc(document_id=document_id, project_id=project_id, name=name, phase_code=phase, updated_by=updated_by)
        version = ProjectDocumentVersionDoc(
            document_id=document_id, project_id=project_id, version=1, phase_code=phase, attachment_id=attachment_id,
            submitted_by=updated_by, reviewers=[DocumentReviewer(user_id=user_id) for user_id in reviewer_ids],
        )
        await document.insert()
        try:
            await version.insert()
        except Exception:
            document.is_deleted = True
            document.updated_at = _now()
            await document.save()
            raise
        return cls._document_dict(document)

    @classmethod
    async def list_documents(cls, project_id: str) -> list[dict[str, Any]]:
        docs = await ProjectDocumentDoc.find({"project_id": project_id, "is_deleted": False}).sort("updated_at", -1).to_list()
        return [cls._document_dict(doc) for doc in docs]

    @classmethod
    async def list_versions(cls, project_id: str, document_id: str) -> list[dict[str, Any]]:
        versions = await ProjectDocumentVersionDoc.find({"project_id": project_id, "document_id": document_id, "is_deleted": False}).sort("version", -1).to_list()
        return [cls._version_dict(version) for version in versions]

    @classmethod
    async def create_version(cls, project_id: str, document_id: str, phase_code: str, attachment_id: str, updated_by: str, reviewer_ids: list[str]) -> dict[str, Any]:
        document = await ProjectDocumentDoc.find_one({"project_id": project_id, "document_id": document_id, "is_deleted": False})
        if not document:
            raise ProjectAssetNotFoundError("项目文档不存在")
        if document.status == ProjectDocumentStatus.IN_REVIEW.value:
            raise ProjectQueryError("当前文档已有版本正在审核")
        if not reviewer_ids or len(set(reviewer_ids)) != len(reviewer_ids):
            raise ProjectQueryError("至少指定一名不重复的审核人")
        members = {member.user_id: member for member in await cls.list_members(document.project_id)}
        if any(user_id not in members for user_id in reviewer_ids):
            raise ProjectQueryError("审核人必须是项目成员")
        if any(members[user_id].role_code not in REVIEWER_ROLES for user_id in reviewer_ids):
            raise ProjectQueryError("审核人必须拥有 PROJECT_REVIEWER 或 PROJECT_ADMIN 角色")
        version_no = document.current_version + 1
        version = ProjectDocumentVersionDoc(
            document_id=document_id, project_id=document.project_id, version=version_no,
            phase_code=cls._validate_phase(phase_code), attachment_id=attachment_id, submitted_by=updated_by,
            reviewers=[DocumentReviewer(user_id=user_id) for user_id in reviewer_ids],
        )
        document.current_version = version_no
        document.phase_code = version.phase_code
        document.status = ProjectDocumentStatus.DRAFT.value
        document.updated_by = updated_by
        await version.insert()
        try:
            await document.save()
        except Exception:
            version.is_deleted = True
            version.updated_at = _now()
            await version.save()
            raise
        return cls._version_dict(version)

    @classmethod
    async def submit_version(cls, project_id: str, document_id: str, version_no: int, actor_id: str) -> dict[str, Any]:
        version = await ProjectDocumentVersionDoc.find_one({"project_id": project_id, "document_id": document_id, "version": version_no, "is_deleted": False})
        document = await ProjectDocumentDoc.find_one({"project_id": project_id, "document_id": document_id, "is_deleted": False})
        if not version or not document:
            raise ProjectAssetNotFoundError("项目文档版本不存在")
        if version.status not in {ProjectDocumentStatus.DRAFT.value, ProjectDocumentStatus.CHANGES_REQUESTED.value}:
            raise ProjectQueryError("当前版本不能重复提交审核")
        if actor_id in {reviewer.user_id for reviewer in version.reviewers}:
            raise ProjectQueryError("提交人不能审核自己的文档版本")
        if version.status == ProjectDocumentStatus.CHANGES_REQUESTED.value:
            for reviewer in version.reviewers:
                reviewer.decision = None
                reviewer.comment = None
                reviewer.reviewed_at = None
        version.status = ProjectDocumentStatus.IN_REVIEW.value
        version.submitted_at = _now()
        document.status = version.status
        document.updated_by = actor_id
        await version.save()
        await document.save()
        return cls._version_dict(version)

    @classmethod
    async def review_version(cls, project_id: str, document_id: str, version_no: int, reviewer_id: str, decision: str, comment: str | None = None) -> dict[str, Any]:
        version = await ProjectDocumentVersionDoc.find_one({"project_id": project_id, "document_id": document_id, "version": version_no, "is_deleted": False})
        document = await ProjectDocumentDoc.find_one({"project_id": project_id, "document_id": document_id, "is_deleted": False})
        if not version or not document:
            raise ProjectAssetNotFoundError("项目文档版本不存在")
        if version.status != ProjectDocumentStatus.IN_REVIEW.value:
            raise ProjectQueryError("当前版本不在审核中")
        if decision not in {item.value for item in ProjectReviewDecision}:
            raise ProjectQueryError("无效的审核结论")
        reviewer = next((item for item in version.reviewers if item.user_id == reviewer_id), None)
        if reviewer is None:
            raise ProjectPermissionError("当前用户不是该版本审核人")
        if reviewer.decision:
            raise ProjectQueryError("当前审核人已经提交过结论")
        reviewer.decision = decision
        reviewer.comment = comment
        reviewer.reviewed_at = _now()
        if decision == ProjectReviewDecision.REQUEST_CHANGES.value:
            version.status = ProjectDocumentStatus.CHANGES_REQUESTED.value
        elif all(item.decision == ProjectReviewDecision.APPROVE.value for item in version.reviewers):
            version.status = ProjectDocumentStatus.APPROVED.value
            version.completed_at = _now()
        document.status = version.status
        document.updated_by = reviewer_id
        await version.save()
        await document.save()
        return cls._version_dict(version)

    @classmethod
    async def list_folders(cls, project_id: str, parent_folder_id: str | None = None) -> list[ProjectFolderDoc]:
        return await ProjectFolderDoc.find({"project_id": project_id, "parent_folder_id": parent_folder_id, "is_deleted": False}).sort("name").to_list()

    @classmethod
    async def create_folder(cls, project_id: str, name: str, parent_folder_id: str | None, created_by: str) -> ProjectFolderDoc:
        parent_folder_id = parent_folder_id or None
        name, normalized = _clean_name(name)
        if await ProjectFileDoc.find_one({"project_id": project_id, "folder_id": parent_folder_id, "normalized_name": normalized, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名项目文件")
        depth = 0
        if parent_folder_id:
            parent = await ProjectFolderDoc.find_one({"folder_id": parent_folder_id, "project_id": project_id, "is_deleted": False})
            if not parent:
                raise ProjectAssetNotFoundError("父文件夹不存在")
            depth = parent.depth + 1
        if depth > 9:
            raise ProjectQueryError("文件夹最多支持 10 级")
        if await ProjectFolderDoc.find_one({"project_id": project_id, "parent_folder_id": parent_folder_id, "normalized_name": normalized, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名文件夹")
        folder = ProjectFolderDoc(folder_id=str(uuid.uuid4()), project_id=project_id, name=name, normalized_name=normalized, parent_folder_id=parent_folder_id, depth=depth, created_by=created_by)
        await folder.insert()
        return folder

    @classmethod
    async def rename_folder(cls, project_id: str, folder_id: str, name: str) -> ProjectFolderDoc:
        folder = await ProjectFolderDoc.find_one({"project_id": project_id, "folder_id": folder_id, "is_deleted": False})
        if not folder:
            raise ProjectAssetNotFoundError("文件夹不存在")
        new_name, new_normalized = _clean_name(name)
        if await ProjectFileDoc.find_one({"project_id": project_id, "folder_id": folder.parent_folder_id, "normalized_name": new_normalized, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名项目文件")
        if await ProjectFolderDoc.find_one({"project_id": project_id, "parent_folder_id": folder.parent_folder_id, "normalized_name": new_normalized, "folder_id": {"$ne": folder_id}, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名文件夹")
        folder.name, folder.normalized_name = new_name, new_normalized
        folder.updated_at = _now()
        await folder.save()
        return folder

    @classmethod
    async def delete_folder(cls, project_id: str, folder_id: str) -> None:
        folder = await ProjectFolderDoc.find_one({"project_id": project_id, "folder_id": folder_id, "is_deleted": False})
        if not folder:
            raise ProjectAssetNotFoundError("文件夹不存在")
        child_folder = await ProjectFolderDoc.find_one({"project_id": project_id, "parent_folder_id": folder_id, "is_deleted": False})
        child_file = await ProjectFileDoc.find_one({"project_id": project_id, "folder_id": folder_id, "is_deleted": False})
        if child_folder or child_file:
            raise ProjectQueryError("只能删除空文件夹")
        folder.is_deleted = True
        folder.updated_at = _now()
        await folder.save()

    @classmethod
    async def move_file(cls, project_id: str, project_file_id: str, folder_id: str | None, actor_id: str) -> ProjectFileDoc:
        folder_id = folder_id or None
        doc = await ProjectFileDoc.find_one({"project_id": project_id, "project_file_id": project_file_id, "is_deleted": False})
        if not doc:
            raise ProjectAssetNotFoundError("项目文件不存在")
        if folder_id and not await ProjectFolderDoc.find_one({"project_id": project_id, "folder_id": folder_id, "is_deleted": False}):
            raise ProjectAssetNotFoundError("目标文件夹不存在")
        if await ProjectFolderDoc.find_one({"project_id": project_id, "parent_folder_id": folder_id, "normalized_name": doc.normalized_name, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名文件夹")
        if await ProjectFileDoc.find_one({"project_id": project_id, "folder_id": folder_id, "normalized_name": doc.normalized_name, "project_file_id": {"$ne": project_file_id}, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名项目文件")
        doc.folder_id = folder_id
        doc.updated_by = actor_id
        doc.updated_at = _now()
        await doc.save()
        return doc

    @classmethod
    async def rename_file(cls, project_id: str, project_file_id: str, name: str, actor_id: str) -> ProjectFileDoc:
        doc = await ProjectFileDoc.find_one({"project_id": project_id, "project_file_id": project_file_id, "is_deleted": False})
        if not doc:
            raise ProjectAssetNotFoundError("项目文件不存在")
        new_name, new_normalized = _clean_name(name)
        if await ProjectFolderDoc.find_one({"project_id": project_id, "parent_folder_id": doc.folder_id, "normalized_name": new_normalized, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名文件夹")
        if await ProjectFileDoc.find_one({"project_id": project_id, "folder_id": doc.folder_id, "normalized_name": new_normalized, "project_file_id": {"$ne": project_file_id}, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名项目文件")
        doc.name, doc.normalized_name = new_name, new_normalized
        doc.updated_by = actor_id
        doc.updated_at = _now()
        await doc.save()
        return doc

    @classmethod
    async def create_file(cls, project_id: str, name: str, folder_id: str | None, attachment_id: str, actor_id: str) -> ProjectFileDoc:
        folder_id = folder_id or None
        name, normalized = _clean_name(name)
        if await ProjectFolderDoc.find_one({"project_id": project_id, "parent_folder_id": folder_id, "normalized_name": normalized, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名文件夹")
        if folder_id and not await ProjectFolderDoc.find_one({"folder_id": folder_id, "project_id": project_id, "is_deleted": False}):
            raise ProjectAssetNotFoundError("文件夹不存在")
        if await ProjectFileDoc.find_one({"project_id": project_id, "folder_id": folder_id, "normalized_name": normalized, "is_deleted": False}):
            raise ProjectQueryError("同级已存在同名项目文件")
        file_doc = ProjectFileDoc(project_file_id=str(uuid.uuid4()), project_id=project_id, folder_id=folder_id, name=name, normalized_name=normalized, attachment_id=attachment_id, created_by=actor_id, updated_by=actor_id)
        await file_doc.insert()
        return file_doc

    @staticmethod
    def file_dict(doc: ProjectFileDoc) -> dict[str, Any]:
        return {"project_file_id": doc.project_file_id, "project_id": doc.project_id, "folder_id": doc.folder_id, "name": doc.name, "attachment_id": doc.attachment_id, "created_by": doc.created_by, "updated_by": doc.updated_by, "updated_at": doc.updated_at}

    @classmethod
    async def list_files(cls, project_id: str, folder_id: str | None = None) -> list[dict[str, Any]]:
        files = await ProjectFileDoc.find({"project_id": project_id, "folder_id": folder_id, "is_deleted": False}).sort("name").to_list()
        return [cls.file_dict(doc) for doc in files]

    @classmethod
    async def delete_file(cls, project_file_id: str) -> None:
        doc = await ProjectFileDoc.find_one({"project_file_id": project_file_id, "is_deleted": False})
        if not doc:
            raise ProjectAssetNotFoundError("项目文件不存在")
        doc.is_deleted = True
        doc.updated_at = _now()
        await doc.save()

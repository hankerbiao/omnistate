from __future__ import annotations

from fastapi import Depends, HTTPException

from app.modules.project.domain.constants import ProjectMemberRole
from app.modules.project.service.project_asset_service import ProjectAssetService
from app.modules.project.repository.models.project import ProjectDoc
from app.shared.auth import get_current_user, is_admin_role


def require_project_roles(*roles: str):
    async def dependency(project_id: str, current_user=Depends(get_current_user)):
        project = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        read_roles = {
            ProjectMemberRole.PROJECT_ADMIN.value, ProjectMemberRole.PROJECT_MAINTAINER.value,
            ProjectMemberRole.PROJECT_REVIEWER.value, ProjectMemberRole.PROJECT_VIEWER.value,
        }
        if is_admin_role(current_user.get("role_ids", [])):
            if project.status == "archived" and set(roles) != read_roles:
                raise HTTPException(status_code=409, detail="归档项目为只读")
            return current_user
        await ProjectAssetService.require_role(project_id, current_user["user_id"], roles)
        if project.status == "archived" and set(roles) != read_roles:
            raise HTTPException(status_code=409, detail="归档项目为只读")
        return current_user
    return dependency


PROJECT_READ = require_project_roles(
    ProjectMemberRole.PROJECT_ADMIN.value, ProjectMemberRole.PROJECT_MAINTAINER.value,
    ProjectMemberRole.PROJECT_REVIEWER.value, ProjectMemberRole.PROJECT_VIEWER.value,
)
PROJECT_WRITE = require_project_roles(ProjectMemberRole.PROJECT_ADMIN.value, ProjectMemberRole.PROJECT_MAINTAINER.value)
PROJECT_ADMIN = require_project_roles(ProjectMemberRole.PROJECT_ADMIN.value)
PROJECT_REVIEW = require_project_roles(ProjectMemberRole.PROJECT_REVIEWER.value, ProjectMemberRole.PROJECT_ADMIN.value)

async def require_project_lifecycle(project_id: str, current_user=Depends(get_current_user)):
    """项目生命周期操作：项目管理员可归档/恢复，资产写入仍受 PROJECT_WRITE 约束。"""
    project = await ProjectDoc.find_one({"project_id": project_id, "is_deleted": False})
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if is_admin_role(current_user.get("role_ids", [])):
        return current_user
    member = await ProjectAssetService.require_role(
        project_id, current_user["user_id"],
        (ProjectMemberRole.PROJECT_ADMIN.value, ProjectMemberRole.PROJECT_MAINTAINER.value),
    )
    if project.status == "archived" and member.role_code != ProjectMemberRole.PROJECT_ADMIN.value:
        raise HTTPException(status_code=409, detail="归档项目只能由项目管理员恢复")
    return current_user

PROJECT_LIFECYCLE = require_project_lifecycle

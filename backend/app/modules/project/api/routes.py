"""项目管理 API 路由。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.project.api.dependencies import ProjectServiceDep
from app.modules.project.service.project_service import ProjectService
from app.modules.project.schemas.project import (
    CreateProjectRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
    UpdateProjectRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=APIResponse[ProjectListResponse])
async def list_projects(
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
    name: Optional[str] = Query(None, description="项目名称（模糊搜索）"),
    key: Optional[str] = Query(None, description="项目标识（模糊搜索）"),
    status: Optional[str] = Query(None, description="项目状态 (active|archived)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 (asc|desc)"),
) -> APIResponse[ProjectListResponse]:
    """获取项目列表。"""
    result = await service.list_projects(
        name=name,
        key=key,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return APIResponse(data=ProjectListResponse(**result))


@router.post("", response_model=APIResponse[ProjectResponse])
async def create_project(
    data: CreateProjectRequest,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """创建项目。"""
    try:
        doc = await service.create_project(
            data=data.model_dump(),
            created_by=current_user.get("username"),
        )
        return APIResponse(
            data=ProjectService._to_project_response(doc),
            message="项目创建成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}", response_model=APIResponse[ProjectDetailResponse])
async def get_project(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectDetailResponse]:
    """获取项目详情（含统计）。"""
    detail = await service.get_project_detail(project_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return APIResponse(data=detail)


@router.put("/{project_id}", response_model=APIResponse[ProjectResponse])
async def update_project(
    project_id: str,
    data: UpdateProjectRequest,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """更新项目。"""
    try:
        doc = await service.update_project(
            project_id=project_id,
            data=data.model_dump(exclude_unset=True),
        )
        return APIResponse(
            data=ProjectService._to_project_response(doc),
            message="项目更新成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}", response_model=APIResponse)
async def delete_project(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse:
    """删除项目（软删除，同时清理关联数据）。"""
    try:
        await service.delete_project(project_id)
        return APIResponse(message="项目已删除")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/stats", response_model=APIResponse[ProjectStatsResponse])
async def get_project_stats(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectStatsResponse]:
    """获取项目统计数据。"""
    stats = await service.get_project_stats(project_id)
    return APIResponse(data=stats)

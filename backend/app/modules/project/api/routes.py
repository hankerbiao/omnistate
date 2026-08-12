"""项目管理 API 路由。"""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.modules.project.api.dependencies import ProjectServiceDep
from app.modules.project.schemas.project import (
    BlockerItemResponse,
    CreateProjectRequest,
    GenerateDemoResponse,
    ProjectActivityResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
    UpdateProjectRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, is_admin_role, require_permission
from app.modules.project.api.asset_dependencies import PROJECT_ADMIN, PROJECT_LIFECYCLE, PROJECT_READ, PROJECT_REVIEW, PROJECT_WRITE
from app.modules.project.domain.exceptions import ProjectAssetNotFoundError, ProjectQueryError
from app.modules.project.repository.models import ProjectDocumentVersionDoc, ProjectFileDoc
from app.modules.project.service.project_asset_service import ProjectAssetService
from app.modules.attachments.service import AttachmentService
from app.modules.project.schemas.project import (
    ProjectDocumentResponse, ProjectDocumentVersionResponse, ProjectFileResponse, ProjectFolderResponse,
    ProjectMemberRequest, ProjectMemberResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=APIResponse[ProjectListResponse], summary="获取项目列表")
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
    visible_project_ids = None
    if not is_admin_role(current_user.get("role_ids", [])):
        members = await ProjectAssetService.list_members_for_user(current_user["user_id"])
        visible_project_ids = {member.project_id for member in members}
    result = await service.list_projects(
        name=name,
        key=key,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        visible_project_ids=visible_project_ids,
    )
    return APIResponse(data=ProjectListResponse(**result))


@router.post("", response_model=APIResponse[ProjectResponse], summary="创建项目", dependencies=[Depends(require_permission("projects:create"))])
async def create_project(
    data: CreateProjectRequest,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """创建项目。"""
    doc = await service.create_project(
        data=data.model_dump(),
        created_by=current_user.get("user_id"),
    )
    return APIResponse(
        data=await service._to_project_response(doc),
        message="项目创建成功",
    )


@router.get("/{project_id}", response_model=APIResponse[ProjectDetailResponse], summary="获取项目详情", dependencies=[Depends(PROJECT_READ)])
async def get_project(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectDetailResponse]:
    """获取项目详情（含统计）。"""
    detail = await service.get_project_detail(project_id)
    return APIResponse(data=detail)


@router.put("/{project_id}", response_model=APIResponse[ProjectResponse], summary="更新项目", dependencies=[Depends(PROJECT_LIFECYCLE)])
async def update_project(
    project_id: str,
    data: UpdateProjectRequest,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectResponse]:
    """更新项目。"""
    doc = await service.update_project(
        project_id=project_id,
        data=data.model_dump(exclude_unset=True),
    )
    return APIResponse(
        data=await service._to_project_response(doc),
        message="项目更新成功",
    )


@router.delete("/{project_id}", response_model=APIResponse, summary="删除项目", dependencies=[Depends(PROJECT_ADMIN)])
async def delete_project(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse:
    """删除项目（软删除，同时清理关联数据）。"""
    await service.delete_project(project_id)
    return APIResponse(message="项目已删除")


@router.get("/{project_id}/stats", response_model=APIResponse[ProjectStatsResponse], summary="获取项目统计数据", dependencies=[Depends(PROJECT_READ)])
async def get_project_stats(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[ProjectStatsResponse]:
    """获取项目统计数据。"""
    stats = await service.get_project_stats(project_id)
    return APIResponse(data=stats)


@router.get("/{project_id}/blockers", response_model=APIResponse[List[BlockerItemResponse]], summary="获取项目风险/阻塞项", dependencies=[Depends(PROJECT_READ)])
async def get_project_blockers(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[List[BlockerItemResponse]]:
    """获取项目风险/阻塞项。"""
    blockers = await service.get_blockers(project_id)
    return APIResponse(data=blockers)


@router.get("/{project_id}/activities", response_model=APIResponse[List[ProjectActivityResponse]], summary="获取项目最近动态", dependencies=[Depends(PROJECT_READ)])
async def get_project_activities(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
) -> APIResponse[List[ProjectActivityResponse]]:
    """获取项目最近动态。"""
    activities = await service.get_activities(project_id, limit=limit)
    return APIResponse(data=activities)


@router.post("/{project_id}/generate-demo-data", response_model=APIResponse[GenerateDemoResponse], summary="生成项目演示数据", dependencies=[Depends(PROJECT_ADMIN)])
async def generate_demo_data(
    project_id: str,
    service: ProjectServiceDep,
    current_user=Depends(get_current_user),
) -> APIResponse[GenerateDemoResponse]:
    """生成项目演示数据。"""
    result = await service.generate_demo_data(project_id)
    return APIResponse(data=result, message="演示数据生成成功")


@router.get("/{project_id}/members", response_model=APIResponse[List[ProjectMemberResponse]], dependencies=[Depends(PROJECT_READ)])
async def list_project_members(project_id: str):
    members = await ProjectAssetService.list_members(project_id)
    return APIResponse(data=[ProjectMemberResponse(user_id=item.user_id, role_code=item.role_code, joined_at=item.joined_at) for item in members])


@router.put("/{project_id}/members/{user_id}", response_model=APIResponse[ProjectMemberResponse], dependencies=[Depends(PROJECT_ADMIN)])
async def upsert_project_member(project_id: str, user_id: str, data: ProjectMemberRequest):
    if data.user_id != user_id:
        raise ProjectQueryError("路径用户与请求用户不一致")
    member = await ProjectAssetService.upsert_member(project_id, user_id, data.role_code)
    return APIResponse(data=ProjectMemberResponse(user_id=member.user_id, role_code=member.role_code, joined_at=member.joined_at))


@router.delete("/{project_id}/members/{user_id}", response_model=APIResponse, dependencies=[Depends(PROJECT_ADMIN)])
async def remove_project_member(project_id: str, user_id: str):
    await ProjectAssetService.remove_member(project_id, user_id)
    return APIResponse(message="项目成员已移除")


def _parse_reviewers(value: str) -> list[str]:
    try:
        reviewers = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ProjectQueryError("reviewer_ids 必须是 JSON 数组") from exc
    if not isinstance(reviewers, list) or not all(isinstance(item, str) and item.strip() for item in reviewers):
        raise ProjectQueryError("reviewer_ids 必须是用户 ID 字符串数组")
    return [item.strip() for item in reviewers]


async def _read_upload(file: UploadFile, max_size: int = 100 * 1024 * 1024) -> bytes:
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > max_size:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="文件大小超过 100MB 限制")
    return bytes(content)


@router.post("/{project_id}/documents", response_model=APIResponse[ProjectDocumentResponse], dependencies=[Depends(PROJECT_WRITE)])
async def create_project_document(
    project_id: str,
    name: str = Form(...),
    phase_code: str = Form(...),
    reviewer_ids: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    attachment_service = AttachmentService()
    attachment = await attachment_service.upload_file(
        filename=file.filename or "document", content=await _read_upload(file),
        content_type=file.content_type or "application/octet-stream", uploaded_by=current_user["user_id"],
    )
    try:
        data = await ProjectAssetService.create_document(project_id, name, phase_code, attachment.file_id, current_user["user_id"], _parse_reviewers(reviewer_ids))
    except Exception:
        await attachment_service.delete_attachment(attachment.file_id)
        raise
    return APIResponse(data=data, message="项目文档创建成功")


@router.get("/{project_id}/documents", response_model=APIResponse[List[ProjectDocumentResponse]], dependencies=[Depends(PROJECT_READ)])
async def list_project_documents(project_id: str):
    return APIResponse(data=await ProjectAssetService.list_documents(project_id))


@router.get("/{project_id}/documents/{document_id}/versions", response_model=APIResponse[List[ProjectDocumentVersionResponse]], dependencies=[Depends(PROJECT_READ)])
async def list_project_document_versions(project_id: str, document_id: str):
    return APIResponse(data=await ProjectAssetService.list_versions(project_id, document_id))


@router.post("/{project_id}/documents/{document_id}/versions", response_model=APIResponse[ProjectDocumentVersionResponse], dependencies=[Depends(PROJECT_WRITE)])
async def create_project_document_version(
    project_id: str, document_id: str, phase_code: str = Form(...), reviewer_ids: str = Form(...), file: UploadFile = File(...), current_user=Depends(get_current_user),
):
    attachment_service = AttachmentService()
    attachment = await attachment_service.upload_file(
        filename=file.filename or "document", content=await _read_upload(file),
        content_type=file.content_type or "application/octet-stream", uploaded_by=current_user["user_id"],
    )
    try:
        version = await ProjectAssetService.create_version(project_id, document_id, phase_code, attachment.file_id, current_user["user_id"], _parse_reviewers(reviewer_ids))
    except Exception:
        await attachment_service.delete_attachment(attachment.file_id)
        raise
    return APIResponse(data=version, message="项目文档版本创建成功")


@router.post("/{project_id}/documents/{document_id}/versions/{version_no}/submit", response_model=APIResponse[ProjectDocumentVersionResponse], dependencies=[Depends(PROJECT_WRITE)])
async def submit_project_document_version(project_id: str, document_id: str, version_no: int, current_user=Depends(get_current_user)):
    return APIResponse(data=await ProjectAssetService.submit_version(project_id, document_id, version_no, current_user["user_id"]), message="文档已提交审核")


@router.post("/{project_id}/documents/{document_id}/versions/{version_no}/reviews", response_model=APIResponse[ProjectDocumentVersionResponse], dependencies=[Depends(PROJECT_REVIEW)])
async def review_project_document_version(project_id: str, document_id: str, version_no: int, decision: str = Form(...), comment: str | None = Form(None), current_user=Depends(get_current_user)):
    return APIResponse(data=await ProjectAssetService.review_version(project_id, document_id, version_no, current_user["user_id"], decision, comment), message="审核结论已提交")


@router.get("/{project_id}/documents/{document_id}/versions/{version_no}/download", response_model=APIResponse[dict], dependencies=[Depends(PROJECT_READ)])
async def download_project_document(project_id: str, document_id: str, version_no: int):
    version = await ProjectDocumentVersionDoc.find_one({"document_id": document_id, "project_id": project_id, "version": version_no, "is_deleted": False})
    if not version:
        raise ProjectAssetNotFoundError("项目文档版本不存在")
    url = await AttachmentService().get_download_url(version.attachment_id, expires_seconds=900)
    if not url:
        raise ProjectAssetNotFoundError("文档主文件不存在或已删除")
    return APIResponse(data={"attachment_id": version.attachment_id, "download_url": url, "expires_in": 900})


@router.post("/{project_id}/folders", response_model=APIResponse[ProjectFolderResponse], dependencies=[Depends(PROJECT_WRITE)])
async def create_project_folder(project_id: str, name: str = Form(...), parent_folder_id: str | None = Form(None), current_user=Depends(get_current_user)):
    folder = await ProjectAssetService.create_folder(project_id, name, parent_folder_id, current_user["user_id"])
    return APIResponse(data=ProjectFolderResponse(folder_id=folder.folder_id, project_id=folder.project_id, name=folder.name, parent_folder_id=folder.parent_folder_id, depth=folder.depth))


@router.get("/{project_id}/folders", response_model=APIResponse[List[ProjectFolderResponse]], dependencies=[Depends(PROJECT_READ)])
async def list_project_folders(project_id: str, parent_folder_id: str | None = Query(None)):
    folders = await ProjectAssetService.list_folders(project_id, parent_folder_id)
    return APIResponse(data=[ProjectFolderResponse(folder_id=item.folder_id, project_id=item.project_id, name=item.name, parent_folder_id=item.parent_folder_id, depth=item.depth) for item in folders])


@router.patch("/{project_id}/folders/{folder_id}", response_model=APIResponse[ProjectFolderResponse], dependencies=[Depends(PROJECT_WRITE)])
async def rename_project_folder(project_id: str, folder_id: str, name: str = Form(...)):
    folder = await ProjectAssetService.rename_folder(project_id, folder_id, name)
    return APIResponse(data=ProjectFolderResponse(folder_id=folder.folder_id, project_id=folder.project_id, name=folder.name, parent_folder_id=folder.parent_folder_id, depth=folder.depth))


@router.delete("/{project_id}/folders/{folder_id}", response_model=APIResponse, dependencies=[Depends(PROJECT_WRITE)])
async def delete_project_folder(project_id: str, folder_id: str):
    await ProjectAssetService.delete_folder(project_id, folder_id)
    return APIResponse(message="项目文件夹已删除")


@router.post("/{project_id}/files", response_model=APIResponse[ProjectFileResponse], dependencies=[Depends(PROJECT_WRITE)])
async def create_project_file(project_id: str, file: UploadFile = File(...), folder_id: str | None = Form(None), name: str | None = Form(None), current_user=Depends(get_current_user)):
    attachment_service = AttachmentService()
    attachment = await attachment_service.upload_file(
        filename=file.filename or "file", content=await _read_upload(file),
        content_type=file.content_type or "application/octet-stream", uploaded_by=current_user["user_id"],
    )
    try:
        doc = await ProjectAssetService.create_file(project_id, name or file.filename or "file", folder_id, attachment.file_id, current_user["user_id"])
    except Exception:
        await attachment_service.delete_attachment(attachment.file_id)
        raise
    return APIResponse(data=ProjectFileResponse(**ProjectAssetService.file_dict(doc)), message="项目文件上传成功")


@router.get("/{project_id}/files", response_model=APIResponse[List[ProjectFileResponse]], dependencies=[Depends(PROJECT_READ)])
async def list_project_files(project_id: str, folder_id: str | None = Query(None)):
    return APIResponse(data=await ProjectAssetService.list_files(project_id, folder_id))


@router.get("/{project_id}/files/{project_file_id}/download", response_model=APIResponse[dict], dependencies=[Depends(PROJECT_READ)])
async def download_project_file(project_id: str, project_file_id: str):
    doc = await ProjectFileDoc.find_one({"project_file_id": project_file_id, "project_id": project_id, "is_deleted": False})
    if not doc:
        raise ProjectAssetNotFoundError("项目文件不存在")
    url = await AttachmentService().get_download_url(doc.attachment_id, expires_seconds=900)
    if not url:
        raise ProjectAssetNotFoundError("项目文件不存在或已删除")
    return APIResponse(data={"attachment_id": doc.attachment_id, "download_url": url, "expires_in": 900})


@router.delete("/{project_id}/files/{project_file_id}", response_model=APIResponse, dependencies=[Depends(PROJECT_WRITE)])
async def delete_project_file(project_id: str, project_file_id: str):
    doc = await ProjectFileDoc.find_one({"project_file_id": project_file_id, "project_id": project_id, "is_deleted": False})
    if not doc:
        raise ProjectAssetNotFoundError("项目文件不存在")
    await ProjectAssetService.delete_file(project_file_id)
    await AttachmentService().delete_attachment(doc.attachment_id)
    return APIResponse(message="项目文件已删除")


@router.patch("/{project_id}/files/{project_file_id}", response_model=APIResponse[ProjectFileResponse], dependencies=[Depends(PROJECT_WRITE)])
async def rename_project_file(project_id: str, project_file_id: str, name: str = Form(...), current_user=Depends(get_current_user)):
    doc = await ProjectAssetService.rename_file(project_id, project_file_id, name, current_user["user_id"])
    return APIResponse(data=ProjectFileResponse(**ProjectAssetService.file_dict(doc)))


@router.patch("/{project_id}/files/{project_file_id}/move", response_model=APIResponse[ProjectFileResponse], dependencies=[Depends(PROJECT_WRITE)])
async def move_project_file(project_id: str, project_file_id: str, folder_id: str | None = Form(None), current_user=Depends(get_current_user)):
    doc = await ProjectAssetService.move_file(project_id, project_file_id, folder_id, current_user["user_id"])
    return APIResponse(data=ProjectFileResponse(**ProjectAssetService.file_dict(doc)))

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.modules.attachments.schemas.attachment import (
    AttachmentInfo,
    AttachmentListResponse,
    DeleteResponse,
    DownloadResponse,
    UploadResponse,
)
from app.modules.attachments.service import AttachmentService
from app.modules.attachments.application import is_attachment_referenced
from app.shared.auth import get_current_user, get_user_permissions, is_admin_role, require_permission

router = APIRouter(prefix="/attachments", tags=["附件管理"])

CurrentUser = Annotated[dict, Depends(get_current_user)]
MAX_UPLOAD_SIZE = 100 * 1024 * 1024
READ_PERMISSION = Depends(require_permission("attachments:read"))
UPLOAD_PERMISSION = Depends(require_permission("attachments:upload"))
DELETE_PERMISSION = Depends(require_permission("attachments:delete"))


def get_service() -> AttachmentService:
    return AttachmentService(reference_checker=is_attachment_referenced)


async def _can_manage_attachments(current_user: dict) -> bool:
    if is_admin_role(current_user.get("role_ids", [])):
        return True
    permissions = set(await get_user_permissions(current_user["user_id"]))
    return "attachments:manage" in permissions


async def _ensure_attachment_access(attachment, current_user: dict) -> None:
    if attachment.uploaded_by == current_user["user_id"]:
        return
    if await _can_manage_attachments(current_user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")


async def _read_limited_file(file: UploadFile, max_size: int = MAX_UPLOAD_SIZE) -> bytes:
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"文件大小超过限制（最大 {max_size // (1024 * 1024)}MB）",
            )
    return bytes(content)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传附件",
    dependencies=[UPLOAD_PERMISSION],
)
async def upload_attachment(
    file: UploadFile = File(..., description="要上传的文件"),
    current_user: CurrentUser = None,
):
    """上传附件到 MinIO 并保存元数据。"""
    content = await _read_limited_file(file)
    attachment_service = get_service()
    return await attachment_service.upload_file(
        filename=file.filename or "unknown",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        uploaded_by=current_user["user_id"],
    )


@router.get("/{file_id}", response_model=AttachmentInfo, summary="获取附件信息", dependencies=[READ_PERMISSION])
async def get_attachment(
    file_id: str,
    current_user: CurrentUser = None,
):
    """根据文件 ID 获取附件详细信息。"""
    attachment_service = get_service()
    attachment = await attachment_service.get_attachment(file_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"附件 {file_id} 不存在")

    await _ensure_attachment_access(attachment, current_user)
    download_url = await attachment_service.get_download_url(file_id)
    return attachment_service.to_info(attachment, download_url=download_url)


@router.get(
    "/{file_id}/download",
    response_model=DownloadResponse,
    summary="获取附件下载链接",
    dependencies=[READ_PERMISSION],
)
async def get_download_url(
    file_id: str,
    expires_seconds: int | None = Query(None, ge=1, le=604800),
    current_user: CurrentUser = None,
):
    """生成预签名下载链接。"""
    attachment_service = get_service()
    attachment = await attachment_service.get_attachment(file_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"附件 {file_id} 不存在")

    await _ensure_attachment_access(attachment, current_user)
    resolved_expires = attachment_service.resolve_expires_seconds(expires_seconds)
    download_url = await attachment_service.get_download_url(file_id, expires_seconds=resolved_expires)
    return DownloadResponse(download_url=download_url, expires_in=resolved_expires)


@router.delete("/{file_id}", response_model=DeleteResponse, summary="删除附件", dependencies=[DELETE_PERMISSION])
async def delete_attachment(
    file_id: str,
    current_user: CurrentUser = None,
):
    """逻辑删除附件。"""
    attachment_service = get_service()
    attachment = await attachment_service.get_attachment(file_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"附件 {file_id} 不存在")

    await _ensure_attachment_access(attachment, current_user)
    deleted = await attachment_service.delete_attachment(file_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"附件 {file_id} 不存在")
    return DeleteResponse(file_id=file_id, deleted=True)


@router.get("", response_model=AttachmentListResponse, summary="列出附件列表", dependencies=[READ_PERMISSION])
async def list_attachments(
    uploaded_by: Optional[str] = None,
    limit: int = Query(100, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: CurrentUser = None,
):
    """列出附件，普通用户只能查看本人附件。"""
    can_manage = await _can_manage_attachments(current_user)
    if not can_manage:
        if uploaded_by and uploaded_by != current_user["user_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        uploaded_by = current_user["user_id"]

    attachment_service = get_service()
    attachments = await attachment_service.list_attachments(uploaded_by=uploaded_by, limit=limit, skip=skip)
    total = await attachment_service.count_attachments(uploaded_by=uploaded_by)
    return AttachmentListResponse(
        items=[attachment_service.to_info(att) for att in attachments],
        total=total,
    )

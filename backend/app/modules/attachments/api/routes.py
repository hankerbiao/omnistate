from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from app.modules.attachments.schemas.attachment import (
    AttachmentInfo,
    AttachmentListResponse,
    DeleteResponse,
    DispatchResponse,
    DownloadResponse,
    UploadResponse,
)
from app.modules.attachments.service import AttachmentService
from app.shared.auth import get_current_user

router = APIRouter(prefix="/attachments", tags=["附件管理"])

# 当前用户类型（从JWT获取）
CurrentUser = Annotated[dict, Depends(get_current_user)]


def get_service() -> AttachmentService:
    """获取服务实例"""
    return AttachmentService()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(..., description="要上传的文件"),
    current_user: CurrentUser = None,
):
    """上传附件

    将文件上传到MinIO并保存元数据到MongoDB

    - **file**: 文件内容（FormData）
    """
    # 读取文件内容
    content = await file.read()

    # 限制文件大小（100MB）
    max_size = 100 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制（最大 {max_size // (1024 * 1024)}MB）",
        )

    # 获取用户ID
    user_id = current_user.get("user_id", "anonymous") if current_user else "anonymous"

    # 上传文件
    attachment_service = get_service()
    result = await attachment_service.upload_file(
        filename=file.filename or "unknown",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        uploaded_by=user_id,
    )

    return result


@router.get("/{file_id}", response_model=AttachmentInfo)
async def get_attachment(
    file_id: str,
    current_user: CurrentUser = None,
):
    """获取附件信息

    根据文件ID获取附件详细信息

    - **file_id**: 文件唯一标识
    """
    attachment_service = get_service()
    info = await attachment_service.get_attachment_info(file_id)

    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"附件 {file_id} 不存在",
        )

    return info


@router.get("/{file_id}/download", response_model=DownloadResponse)
async def get_download_url(
    file_id: str,
    expires_seconds: int = 3600,
    current_user: CurrentUser = None,
):
    """获取下载链接

    生成预签名下载链接

    - **file_id**: 文件唯一标识
    - **expires_seconds**: 链接有效期（秒），默认3600秒
    """
    attachment_service = get_service()
    download_url = await attachment_service.get_download_url(
        file_id, expires_seconds=expires_seconds
    )

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"附件 {file_id} 不存在",
        )

    return DownloadResponse(download_url=download_url, expires_in=expires_seconds)


@router.delete("/{file_id}", response_model=DeleteResponse)
async def delete_attachment(
    file_id: str,
    current_user: CurrentUser = None,
):
    """删除附件

    逻辑删除附件

    - **file_id**: 文件唯一标识
    """
    attachment_service = get_service()
    deleted = await attachment_service.delete_attachment(file_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"附件 {file_id} 不存在",
        )

    return DeleteResponse(file_id=file_id, deleted=True)


@router.get("", response_model=AttachmentListResponse)
async def list_attachments(
    uploaded_by: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: CurrentUser = None,
):
    """列出附件

    获取附件列表，支持按上传人筛选

    - **uploaded_by**: 上传人ID（可选）
    - **limit**: 返回数量限制，默认100
    - **skip**: 跳过数量，默认0
    """
    attachment_service = get_service()
    attachments = await attachment_service.list_attachments(
        uploaded_by=uploaded_by,
        limit=limit,
        skip=skip,
    )
    total = await attachment_service.count_attachments(uploaded_by=uploaded_by)

    items = [
        AttachmentInfo(
            file_id=att.file_id,
            original_filename=att.original_filename,
            storage_path=f"{att.bucket}/{att.object_name}",
            size=att.size,
            content_type=att.content_type,
            uploaded_by=att.uploaded_by,
            uploaded_at=att.uploaded_at,
            download_url=None,  # 列表不返回下载链接，需要单独请求
        )
        for att in attachments
    ]

    return AttachmentListResponse(items=items, total=total)

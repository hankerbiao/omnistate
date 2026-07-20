import asyncio
import hashlib
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import List, Optional

from app.modules.attachments.repository.models import AttachmentDoc
from app.modules.attachments.schemas.attachment import AttachmentInfo, UploadResponse
from app.shared.domain.exceptions import ConflictError
from app.shared.minio import get_minio_client

AttachmentReferenceChecker = Callable[[str], Awaitable[bool]]


async def _no_references(_: str) -> bool:
    return False


class AttachmentService:
    """附件服务"""

    def __init__(self, reference_checker: AttachmentReferenceChecker | None = None):
        self.minio_client = get_minio_client()
        self._reference_checker = reference_checker or _no_references

    def resolve_expires_seconds(self, expires_seconds: int | None = None) -> int:
        if expires_seconds is not None:
            return expires_seconds
        return self.minio_client.config.presigned_url_expires_seconds

    @staticmethod
    def to_info(attachment: AttachmentDoc, download_url: str | None = None) -> AttachmentInfo:
        return AttachmentInfo(
            file_id=attachment.file_id,
            original_filename=attachment.original_filename,
            storage_path=f"{attachment.bucket}/{attachment.object_name}",
            size=attachment.size,
            content_type=attachment.content_type,
            sha256=attachment.sha256,
            uploaded_by=attachment.uploaded_by,
            uploaded_at=attachment.uploaded_at,
            download_url=download_url,
        )

    async def enrich_for_dispatch(
        self,
        file_ids: List[str],
    ) -> List[dict]:
        """批量校验附件并补充 MinIO 元数据，供任务下发使用。"""
        if not file_ids:
            return []

        docs = await AttachmentDoc.find({
            "file_id": {"$in": file_ids},
            "is_deleted": False,
        }).to_list()
        doc_map = {doc.file_id: doc for doc in docs}

        enriched: List[dict] = []
        for file_id in file_ids:
            doc = doc_map.get(file_id)
            if not doc:
                raise KeyError(f"attachment not found or deleted: {file_id}")
            enriched.append({
                "file_id": doc.file_id,
                "original_filename": doc.original_filename,
                "storage_path": f"{doc.bucket}/{doc.object_name}",
                "bucket": doc.bucket,
                "object_name": doc.object_name,
                "size": doc.size,
                "content_type": doc.content_type,
                "sha256": doc.sha256,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            })
        return enriched

    async def enrich_single(self, file_id: str) -> dict:
        """Enrich a single file for per-case dispatch, including a fresh presigned download URL."""
        doc = await AttachmentDoc.find_one({"file_id": file_id, "is_deleted": False})
        if not doc:
            raise KeyError(f"attachment not found or deleted: {file_id}")
        download_url = await asyncio.to_thread(
            self.minio_client.presigned_get_object, doc.object_name
        )
        return {
            "file_id": doc.file_id,
            "original_filename": doc.original_filename,
            "storage_path": f"{doc.bucket}/{doc.object_name}",
            "bucket": doc.bucket,
            "object_name": doc.object_name,
            "size": doc.size,
            "content_type": doc.content_type,
            "sha256": doc.sha256,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "download_url": download_url,
        }

    async def upload_file(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        uploaded_by: str,
    ) -> UploadResponse:
        """上传文件到 MinIO，并保存附件元数据。"""
        file_id = str(uuid.uuid4())
        extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
        object_name = f"attachments/{file_id}.{extension}" if extension else f"attachments/{file_id}"
        sha256_hash = hashlib.sha256(content).hexdigest()
        bucket = self.minio_client.get_bucket()
        uploaded = False

        try:
            await asyncio.to_thread(
                self.minio_client.put_object,
                object_name=object_name,
                data=content,
                content_type=content_type,
                length=len(content),
            )
            uploaded = True

            attachment = AttachmentDoc(
                file_id=file_id,
                original_filename=filename,
                bucket=bucket,
                object_name=object_name,
                size=len(content),
                content_type=content_type,
                sha256=sha256_hash,
                uploaded_by=uploaded_by,
                uploaded_at=datetime.now(timezone.utc),
                is_deleted=False,
            )
            await attachment.create()
        except Exception as e:
            if uploaded:
                try:
                    await asyncio.to_thread(self.minio_client.remove_object, object_name)
                except Exception:
                    pass
            raise RuntimeError(
                f"Failed to upload file {file_id} for user {uploaded_by}: {e}"
            ) from e

        return UploadResponse(
            file_id=file_id,
            original_filename=filename,
            storage_path=f"{bucket}/{object_name}",
            size=len(content),
            content_type=content_type,
            sha256=sha256_hash,
            uploaded_at=attachment.uploaded_at,
        )

    async def get_attachment(self, file_id: str) -> Optional[AttachmentDoc]:
        """获取未删除附件文档。"""
        return await AttachmentDoc.find_one(
            {"file_id": file_id, "is_deleted": False}
        )

    async def list_attachments(
        self,
        uploaded_by: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[AttachmentDoc]:
        """列出未删除附件。"""
        query = {"is_deleted": False}
        if uploaded_by:
            query["uploaded_by"] = uploaded_by

        return await AttachmentDoc.find(query).skip(skip).limit(limit).to_list()

    async def count_attachments(self, uploaded_by: Optional[str] = None) -> int:
        """统计未删除附件数量。"""
        query = {"is_deleted": False}
        if uploaded_by:
            query["uploaded_by"] = uploaded_by

        return await AttachmentDoc.find(query).count()

    async def delete_attachment(self, file_id: str) -> bool:
        """逻辑删除未被业务引用的附件。"""
        attachment = await self.get_attachment(file_id)
        if not attachment:
            return False
        if await self._reference_checker(file_id):
            raise ConflictError(f"附件 {file_id} 已被业务数据引用，不能删除")

        attachment.is_deleted = True
        attachment.deleted_at = datetime.now(timezone.utc)
        await attachment.update()
        return True

    async def get_download_url(
        self,
        file_id: str,
        expires_seconds: int | None = None,
    ) -> Optional[str]:
        """获取预签名下载链接。"""
        attachment = await self.get_attachment(file_id)
        if not attachment:
            return None

        return await asyncio.to_thread(
            self.minio_client.presigned_get_object,
            attachment.object_name,
            expires_seconds=self.resolve_expires_seconds(expires_seconds),
        )

    async def get_attachment_info(self, file_id: str) -> Optional[AttachmentInfo]:
        """获取附件详细信息（含下载链接）。"""
        attachment = await self.get_attachment(file_id)
        if not attachment:
            return None

        download_url = await self.get_download_url(file_id)
        return self.to_info(attachment, download_url=download_url)

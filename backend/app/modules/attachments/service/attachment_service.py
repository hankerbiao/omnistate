import uuid
from datetime import datetime
from typing import List, Optional

from app.modules.attachments.repository.models import AttachmentDoc
from app.modules.attachments.schemas.attachment import AttachmentInfo, UploadResponse
from app.shared.minio.client import DEFAULT_PRESIGNED_URL_EXPIRES_SECONDS
from app.shared.minio import get_minio_client


class AttachmentService:
    """附件服务"""

    def __init__(self):
        self.minio_client = get_minio_client()

    async def upload_file(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        uploaded_by: str,
    ) -> UploadResponse:
        """上传文件

        Args:
            filename: 原始文件名
            content: 文件内容
            content_type: MIME类型
            uploaded_by: 上传人ID

        Returns:
            上传响应
        """
        # 生成唯一文件ID和对象名
        file_id = str(uuid.uuid4())
        extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
        object_name = f"attachments/{file_id}.{extension}" if extension else f"attachments/{file_id}"

        # 上传到MinIO
        bucket = self.minio_client.get_bucket()
        self.minio_client.put_object(
            object_name=object_name,
            data=content,
            content_type=content_type,
            length=len(content),
        )

        # 保存元数据到MongoDB
        attachment = AttachmentDoc(
            file_id=file_id,
            original_filename=filename,
            bucket=bucket,
            object_name=object_name,
            size=len(content),
            content_type=content_type,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            is_deleted=False,
        )
        await attachment.create()

        return UploadResponse(
            file_id=file_id,
            original_filename=filename,
            storage_path=f"{bucket}/{object_name}",
            size=len(content),
            content_type=content_type,
            uploaded_at=attachment.uploaded_at,
        )

    async def get_attachment(self, file_id: str) -> Optional[AttachmentDoc]:
        """获取附件信息

        Args:
            file_id: 文件ID

        Returns:
            附件文档（未删除），不存在返回None
        """
        return await AttachmentDoc.find_one(
            {"file_id": file_id, "is_deleted": False}
        )

    async def list_attachments(
        self,
        uploaded_by: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> List[AttachmentDoc]:
        """列出附件

        Args:
            uploaded_by: 上传人ID（可选）
            limit: 限制数量
            skip: 跳过数量

        Returns:
            附件列表
        """
        query = {"is_deleted": False}
        if uploaded_by:
            query["uploaded_by"] = uploaded_by

        return await AttachmentDoc.find(query).skip(skip).limit(limit).to_list()

    async def count_attachments(self, uploaded_by: Optional[str] = None) -> int:
        """统计附件数量

        Args:
            uploaded_by: 上传人ID（可选）

        Returns:
            数量
        """
        query = {"is_deleted": False}
        if uploaded_by:
            query["uploaded_by"] = uploaded_by

        return await AttachmentDoc.find(query).count()

    async def delete_attachment(self, file_id: str) -> bool:
        """删除附件（逻辑删除）

        Args:
            file_id: 文件ID

        Returns:
            是否删除成功
        """
        attachment = await self.get_attachment(file_id)
        if not attachment:
            return False

        # 逻辑删除
        attachment.is_deleted = True
        attachment.deleted_at = datetime.utcnow()
        await attachment.update()

        # 可选：物理删除MinIO中的文件（根据需求决定是否立即删除）
        # self.minio_client.remove_object(attachment.object_name)

        return True

    async def get_download_url(
        self,
        file_id: str,
        expires_seconds: int = DEFAULT_PRESIGNED_URL_EXPIRES_SECONDS,
    ) -> Optional[str]:
        """获取下载链接

        Args:
            file_id: 文件ID
            expires_seconds: 过期时间（秒）

        Returns:
            预签名下载链接，不存在返回None
        """
        attachment = await self.get_attachment(file_id)
        if not attachment:
            return None

        return self.minio_client.presigned_get_object(
            attachment.object_name,
            expires_seconds=expires_seconds,
        )

    async def get_attachment_info(self, file_id: str) -> Optional[AttachmentInfo]:
        """获取附件详细信息（含下载链接）

        Args:
            file_id: 文件ID

        Returns:
            附件信息，不存在返回None
        """
        attachment = await self.get_attachment(file_id)
        if not attachment:
            return None

        download_url = await self.get_download_url(file_id)

        return AttachmentInfo(
            file_id=attachment.file_id,
            original_filename=attachment.original_filename,
            storage_path=f"{attachment.bucket}/{attachment.object_name}",
            size=attachment.size,
            content_type=attachment.content_type,
            uploaded_by=attachment.uploaded_by,
            uploaded_at=attachment.uploaded_at,
            download_url=download_url,
        )

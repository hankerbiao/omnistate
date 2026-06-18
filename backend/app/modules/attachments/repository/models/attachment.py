from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field

from app.shared.core.document_mixins import TimestampedDocumentMixin, SoftDeleteDocumentMixin


class AttachmentDoc(Document, TimestampedDocumentMixin, SoftDeleteDocumentMixin):
    """附件文档模型"""

    file_id: str = Field(description="文件唯一标识")
    original_filename: str = Field(description="原始文件名")
    bucket: str = Field(description="MinIO存储桶名称")
    object_name: str = Field(description="MinIO对象名")
    size: int = Field(description="文件大小（字节）")
    content_type: str = Field(description="MIME类型")
    sha256: Optional[str] = Field(default=None, description="文件 SHA256 校验和")
    uploaded_by: str = Field(description="上传人ID")
    uploaded_at: datetime = Field(description="上传时间")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")

    class Settings:
        name = "attachments"
        use_revision = True
        indexes = [
            "file_id",
            "uploaded_by",
        ]

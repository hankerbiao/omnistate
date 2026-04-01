from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class AttachmentDoc(Document):
    """附件文档模型"""

    file_id: str = Field(alias="file_id", description="文件唯一标识")
    original_filename: str = Field(alias="original_filename", description="原始文件名")
    bucket: str = Field(alias="bucket", description="MinIO存储桶名称")
    object_name: str = Field(alias="object_name", description="MinIO对象名")
    size: int = Field(alias="size", description="文件大小（字节）")
    content_type: str = Field(alias="content_type", description="MIME类型")
    uploaded_by: str = Field(alias="uploaded_by", description="上传人ID")
    uploaded_at: datetime = Field(alias="uploaded_at", description="上传时间")
    is_deleted: bool = Field(default=False, alias="is_deleted", description="逻辑删除标记")
    deleted_at: Optional[datetime] = Field(default=None, alias="deleted_at", description="删除时间")

    class Settings:
        name = "attachments"
        use_revision = True
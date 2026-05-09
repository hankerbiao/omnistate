from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Insert, Save, before_event
from pydantic import Field


class AttachmentDoc(Document):
    """附件文档模型"""

    file_id: str = Field(description="文件唯一标识")
    original_filename: str = Field(description="原始文件名")
    bucket: str = Field(description="MinIO存储桶名称")
    object_name: str = Field(description="MinIO对象名")
    size: int = Field(description="文件大小（字节）")
    content_type: str = Field(description="MIME类型")
    uploaded_by: str = Field(description="上传人ID")
    uploaded_at: datetime = Field(description="上传时间")
    is_deleted: bool = Field(default=False, description="逻辑删除标记")
    deleted_at: Optional[datetime] = Field(default=None, description="删除时间")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "attachments"
        use_revision = True
        indexes = [
            "file_id",
            "uploaded_by",
        ]
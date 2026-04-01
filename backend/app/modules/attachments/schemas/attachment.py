from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """文件上传响应"""

    file_id: str = Field(description="文件唯一标识")
    original_filename: str = Field(description="原始文件名")
    storage_path: str = Field(description="MinIO存储路径（bucket/object_name）")
    size: int = Field(description="文件大小（字节）")
    content_type: str = Field(description="MIME类型")
    uploaded_at: datetime = Field(description="上传时间")


class AttachmentInfo(BaseModel):
    """附件信息"""

    file_id: str = Field(description="文件唯一标识")
    original_filename: str = Field(description="原始文件名")
    storage_path: str = Field(description="MinIO存储路径")
    size: int = Field(description="文件大小（字节）")
    content_type: str = Field(description="MIME类型")
    uploaded_by: str = Field(description="上传人ID")
    uploaded_at: datetime = Field(description="上传时间")
    download_url: Optional[str] = Field(default=None, description="下载链接")


class AttachmentListResponse(BaseModel):
    """附件列表响应"""

    items: List[AttachmentInfo] = Field(description="附件列表")
    total: int = Field(description="总数")


class DeleteResponse(BaseModel):
    """删除响应"""

    file_id: str = Field(description="文件ID")
    deleted: bool = Field(description="是否删除成功")


class DownloadResponse(BaseModel):
    """下载链接响应"""

    download_url: str = Field(description="下载链接")
    expires_in: int = Field(description="有效期（秒）")


class DispatchResponse(BaseModel):
    """下发响应"""

    file_id: str = Field(description="文件ID")
    status: str = Field(description="状态")
    message: str = Field(description="说明")
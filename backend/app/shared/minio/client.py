import io
from typing import Optional

from minio import Minio
from minio.error import S3Error

from ..minio.config import MinIOConfig, load_minio_config


class MinIOClientWrapper:
    """MinIO客户端封装"""

    def __init__(self, config: Optional[MinIOConfig] = None):
        self.config = config or load_minio_config()
        self._client: Optional[Minio] = None
        self._bucket = self.config.bucket

    @property
    def client(self) -> Minio:
        """获取MinIO客户端（延迟初始化）"""
        if self._client is None:
            self._client = Minio(
                endpoint=self.config.endpoint,
                access_key=self.config.access_key,
                secret_key=self.config.secret_key,
                secure=self.config.secure,
            )
            # 确保存储桶存在
            self._ensure_bucket()
        return self._client

    def _ensure_bucket(self) -> None:
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self._bucket):
                self.client.make_bucket(self._bucket)
        except S3Error as e:
            raise RuntimeError(f"Failed to ensure bucket {self._bucket}: {e}")

    def put_object(
        self,
        object_name: str,
        data: bytes,
        content_type: str,
        length: Optional[int] = None,
    ) -> None:
        """上传对象

        Args:
            object_name: 对象名（不含bucket前缀）
            data: 文件内容
            content_type: MIME类型
            length: 文件大小（可选，默认自动计算）
        """
        try:
            data_stream = io.BytesIO(data)
            self.client.put_object(
                bucket_name=self._bucket,
                object_name=object_name,
                data=data_stream,
                length=length or len(data),
                content_type=content_type,
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to upload object {object_name}: {e}")

    def get_object(self, object_name: str) -> bytes:
        """获取对象内容

        Args:
            object_name: 对象名

        Returns:
            对象内容
        """
        try:
            response = self.client.get_object(bucket_name=self._bucket, object_name=object_name)
            return response.read()
        except S3Error as e:
            raise RuntimeError(f"Failed to get object {object_name}: {e}")

    def remove_object(self, object_name: str) -> None:
        """删除对象

        Args:
            object_name: 对象名
        """
        try:
            self.client.remove_object(bucket_name=self._bucket, object_name=object_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to remove object {object_name}: {e}")

    def stat_object(self, object_name: str) -> dict:
        """获取对象元数据

        Args:
            object_name: 对象名

        Returns:
            元数据字典（包含size、content_type等）
        """
        try:
            stat = self.client.stat_object(bucket_name=self._bucket, object_name=object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "etag": stat.etag,
            }
        except S3Error as e:
            raise RuntimeError(f"Failed to stat object {object_name}: {e}")

    def presigned_get_object(self, object_name: str, expires_seconds: int = 3600) -> str:
        """生成预签名下载链接

        Args:
            object_name: 对象名
            expires_seconds: 过期时间（秒）

        Returns:
            预签名URL
        """
        try:
            return self.client.presigned_get_object(
                bucket_name=self._bucket,
                object_name=object_name,
                expires=expires_seconds,
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL for {object_name}: {e}")

    def get_bucket(self) -> str:
        """获取存储桶名称"""
        return self._bucket


# 全局客户端实例
_minio_client: Optional[MinIOClientWrapper] = None


def get_minio_client() -> MinIOClientWrapper:
    """获取全局MinIO客户端实例"""
    global _minio_client
    if _minio_client is None:
        _minio_client = MinIOClientWrapper()
    return _minio_client
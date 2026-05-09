"""MinIO 对象存储模块配置。"""

from app.shared.config import MinIOConfig, get_settings


def load_minio_config() -> MinIOConfig:
    return get_settings().minio


__all__ = ["MinIOConfig", "load_minio_config"]
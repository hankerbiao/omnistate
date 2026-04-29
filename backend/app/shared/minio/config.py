"""MinIO 对象存储模块配置。

配置从 config.yaml 统一加载，参考 app/shared/config/settings.py
"""

from app.shared.config import MinIOConfig, load_minio_config

__all__ = ["MinIOConfig", "load_minio_config"]
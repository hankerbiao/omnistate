from dataclasses import dataclass, field
from os import getenv


@dataclass
class MinIOConfig:
    """MinIO配置类"""

    endpoint: str = field(default_factory=lambda: getenv("MINIO_ENDPOINT", "localhost:9000"))
    access_key: str = field(default_factory=lambda: getenv("MINIO_ACCESS_KEY", "minioadmin"))
    secret_key: str = field(default_factory=lambda: getenv("MINIO_SECRET_KEY", "minioadmin"))
    bucket: str = field(default_factory=lambda: getenv("MINIO_BUCKET", "attachments"))
    secure: bool = field(default_factory=lambda: getenv("MINIO_SECURE", "false").lower() == "true")


def load_minio_config() -> MinIOConfig:
    """加载MinIO配置"""
    return MinIOConfig()
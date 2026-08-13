"""Single-source application configuration.

This branch keeps one runtime configuration entrypoint only:
``backend/config/config.yaml`` mounted in containers as ``/run/dml/config.yaml``.
No environment overlay, runtime database config, or secondary config file is used.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from pydantic import BaseModel, ConfigDict, Field, field_validator


CONFIG_FILE_PATH = Path("/run/dml/config.yaml")
ENVIRONMENT_VARIABLE_PATTERN = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")
INSECURE_SECRET_VALUES = frozenset({"CHANGE_ME", "CHANGEME", "SECRET", "DEFAULT"})


class StrictConfigModel(BaseModel):
    """Base model that rejects misspelled configuration keys at every level."""

    model_config = ConfigDict(extra="forbid")


class AppConfig(StrictConfigModel):
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8801
    service_name: str
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8080"])
    trusted_proxies: list[str] = Field(default_factory=list)
    dev_bypass_auth: bool = False
    dev_user_id: str = "dev_admin"


class MongoDBConfig(StrictConfigModel):
    uri: str = "mongodb://mongo:27017"
    db_name: str = "dmlv4_lite"


class MinIOConfig(StrictConfigModel):
    endpoint: str = "minio:9000"
    access_key: str = Field(min_length=3)
    secret_key: str = Field(min_length=8)
    bucket: str = "attachments"
    secure: bool = False
    presigned_url_expires_seconds: int = 7 * 24 * 60 * 60

    @field_validator("access_key", "secret_key")
    @classmethod
    def reject_default_credentials(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.lower() == "minioadmin":
            raise ValueError("MinIO default credentials are not permitted")
        return normalized


class JWTConfig(StrictConfigModel):
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    expire_minutes: int = 480
    issuer: str = "dmlv4-lite"
    audience: str = "dmlv4-lite-web"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        normalized = value.strip()
        if normalized.upper() in INSECURE_SECRET_VALUES:
            raise ValueError("jwt.secret_key must not use a default placeholder")
        return normalized


class RabbitMQConfig(StrictConfigModel):
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    heartbeat: int = 60
    blocked_connection_timeout: int = 30
    connection_attempts: int = 3
    retry_delay: float = 2.0
    ssl_enabled: bool = False
    task_queue: str = "dml_task_queue"
    task_exchange: str = ""
    task_routing_key: str = "dml_task_queue"
    dead_letter_exchange: str = "dml_dlx"
    dead_letter_routing_key: str = "dml_dead_letter"
    prefetch_count: int = 10


class KafkaProducerOptions(StrictConfigModel):
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 10


class KafkaConsumerOptions(StrictConfigModel):
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 100
    consumer_timeout_ms: int = 1000


class KafkaConfig(StrictConfigModel):
    bootstrap_servers: list[str] = Field(default_factory=lambda: ["localhost:9092"])
    client_id: str = "dmlv4-shard"
    result_topic: str = "dmlv4.results"
    dead_letter_topic: str = "dmlv4.deadletter"
    test_events_topic: str = "test-events"
    test_events_group_id: str = "dmlv4-test-events-consumers"
    producer_options: KafkaProducerOptions = Field(default_factory=KafkaProducerOptions)
    consumer_options: KafkaConsumerOptions = Field(default_factory=KafkaConsumerOptions)


class RedisConfig(StrictConfigModel):
    sentinel_hosts: list[str] = Field(default_factory=lambda: ["localhost:26379"])
    master_name: str = "redis_master"
    username: str = ""
    password: str = ""
    db: int = 0
    socket_timeout: int = 2
    max_connections: int = 100
    protocol: int = 2
    retry_on_timeout: bool = True
    sentinel_socket_timeout: float = 0.5
    service_registry_key: str = "dmlv4:service_registry"


class GuangQuanConfig(StrictConfigModel):
    api_url: str = "http://rdm.cooacloud.com/api/platform/notify/bot"
    component_name: str = "DML"
    timeout_sec: int = 5


class NotificationConfig(StrictConfigModel):
    enabled: bool = False
    batch_window_seconds: int = 300
    max_detail_items: int = 10
    guangquan: GuangQuanConfig = Field(default_factory=GuangQuanConfig)


class OpenPlatformGatewayJWTConfig(StrictConfigModel):
    enabled: bool = False
    secret_key: str = ""
    algorithm: str = "HS256"
    issuer: str = "dml-open-platform"
    audience: str = "dml-backend"
    required_token_use: str = "open_platform_gateway"


class LoggingRetentionConfig(StrictConfigModel):
    info_days: int = 7
    error_days: int = 30
    debug_days: int = 3


class LoggingConfig(StrictConfigModel):
    console_level: str = "INFO"
    log_dir: str = "logs"
    retention: LoggingRetentionConfig = Field(default_factory=LoggingRetentionConfig)
    json_format: bool = True
    enable_compress: bool = True
    trace_enabled: bool = True
    slow_query_threshold_ms: int = 200
    slow_request_threshold_ms: int = 800
    module_levels: dict[str, str] = Field(default_factory=dict)


class BootstrapSettings(StrictConfigModel):

    app: AppConfig
    mongodb: MongoDBConfig
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    jwt: JWTConfig
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    open_platform_gateway_jwt: OpenPlatformGatewayJWTConfig = Field(
        default_factory=OpenPlatformGatewayJWTConfig
    )
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class Settings(BootstrapSettings):
    pass


class RuntimeSettings(StrictConfigModel):
    """Compatibility placeholder for the removed runtime-config layer."""

    model_config = ConfigDict(extra="forbid")

    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    jwt: JWTConfig
    redis: RedisConfig = Field(default_factory=RedisConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    open_platform_gateway_jwt: OpenPlatformGatewayJWTConfig = Field(
        default_factory=OpenPlatformGatewayJWTConfig
    )


def _resolve_environment_variables(value: Any, *, path: str = "") -> Any:
    """Resolve whole-value ${ENV_VAR} references without logging secret values."""
    if isinstance(value, dict):
        return {
            key: _resolve_environment_variables(item, path=f"{path}.{key}" if path else key)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_environment_variables(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    if not isinstance(value, str):
        return value

    match = ENVIRONMENT_VARIABLE_PATTERN.fullmatch(value)
    if match is None:
        return value

    variable_name = match.group(1)
    resolved = os.getenv(variable_name)
    if not resolved:
        raise ValueError(f"configuration value {path} requires environment variable {variable_name}")
    return resolved


def load_yaml_config(config_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path is not None else get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {path}\n请挂载 backend/config/config.yaml 到 /run/dml/config.yaml"
        )
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if not isinstance(config, dict):
        raise ValueError(f"configuration root must be a mapping: {path}")
    return _resolve_environment_variables(config)


def get_config_path() -> Path:
    """Return the single supported config file path.

    Preference order:
    1. Explicit CONFIG_PATH, when provided.
    2. The mounted container path /run/dml/config.yaml.
    3. The repository-local backend/config/config.yaml for tests and local runs.
    """

    env_path = os.getenv("CONFIG_PATH")
    if env_path:
        return Path(env_path)

    if CONFIG_FILE_PATH.exists():
        return CONFIG_FILE_PATH

    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        candidate = parent / "config" / "config.yaml"
        if candidate.exists() and candidate.parent.name == "config":
            return candidate

    return Path.cwd() / "config" / "config.yaml"


@lru_cache
def get_bootstrap_settings() -> BootstrapSettings:
    return BootstrapSettings(**load_yaml_config())


@lru_cache
def get_settings() -> Settings:
    return Settings(**get_bootstrap_settings().model_dump())


def clear_runtime_settings() -> None:
    get_bootstrap_settings.cache_clear()
    get_settings.cache_clear()


def get_environment() -> str:
    return os.getenv("DML_ENV", "production").strip().lower() or "production"


def install_runtime_settings(_runtime: object) -> Settings:
    """Compatibility shim for removed runtime settings.

    The single-config branch no longer installs runtime settings separately.
    """
    return get_settings()

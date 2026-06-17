"""统一配置模块 - 从 config.yaml 加载所有服务配置。"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from pydantic import BaseModel, Field


# =============================================================================
# 配置路径
# =============================================================================
def get_config_path() -> Path:
    """获取配置文件路径。

    查找顺序：
    1. 环境变量 CONFIG_PATH 指定的路径
    2. 项目根目录的 config.yaml
    """
    env_path = os.getenv("CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # 向上查找项目根目录（包含 config.yaml 的目录）
    current = Path(__file__).resolve()
    for parent in [current.parent, *current.parents]:
        config_path = parent / "config.yaml"
        if config_path.exists():
            # 确保找到的是 backend 目录或上级目录
            if (parent / "requirements.txt").exists() or (parent.parent / "requirements.txt").exists():
                return config_path

    # 默认使用当前工作目录
    return Path.cwd() / "config.yaml"


# =============================================================================
# 子配置类
# =============================================================================
class AppConfig(BaseModel):
    """应用基础配置。"""

    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8801
    service_name: str = "dmlv4-backend"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class MongoDBConfig(BaseModel):
    """MongoDB 配置。"""

    uri: str = "mongodb://localhost:27017"
    db_name: str = "workflow_db"


class RabbitMQConfig(BaseModel):
    """RabbitMQ 配置。"""

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

    # 任务下发队列
    task_queue: str = "dml_task_queue"
    task_exchange: str = ""
    task_routing_key: str = "dml_task_queue"

    # 死信队列配置（需与 RabbitMQ 服务端已存在的队列参数一致）
    dead_letter_exchange: str = "dml_dlx"
    dead_letter_routing_key: str = "dml_dead_letter"

    # 消费者预取数量
    prefetch_count: int = 10


class KafkaProducerOptions(BaseModel):
    """Kafka Producer 选项。"""

    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 10
    buffer_memory: int = 33554432


class KafkaConsumerOptions(BaseModel):
    """Kafka Consumer 选项。"""

    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 100
    consumer_timeout_ms: int = 1000


class KafkaConfig(BaseModel):
    """Kafka 配置。"""

    bootstrap_servers: list[str] = Field(default_factory=lambda: ["localhost:9092"])
    client_id: str = "dmlv4-shard"

    result_topic: str = "dmlv4.results"
    dead_letter_topic: str = "dmlv4.deadletter"
    test_events_topic: str = "test-events"

    execution_result_group_id: str = "dmlv4-execution-result-consumers"
    test_events_group_id: str = "dmlv4-test-events-consumers"

    producer_options: KafkaProducerOptions = Field(default_factory=KafkaProducerOptions)
    consumer_options: KafkaConsumerOptions = Field(default_factory=KafkaConsumerOptions)


class MinIOConfig(BaseModel):
    """MinIO 配置。"""

    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "attachments"
    secure: bool = False
    presigned_url_expires_seconds: int = 7 * 24 * 60 * 60


class JWTConfig(BaseModel):
    """JWT 认证配置。"""

    secret_key: str = "CHANGE_ME"
    algorithm: str = "HS256"
    expire_minutes: int = 480
    issuer: str = "tcm-backend"
    audience: str = "tcm-frontend"


class ExecutionConfig(BaseModel):
    """任务执行配置。"""

    scheduler_interval_sec: int = 60
    default_repo_url: str = ""
    default_branch: str = "master"
    kafka_worker_agent_id: str = "execution-kafka-worker"
    kafka_worker_heartbeat_ttl_sec: int = 30
    kafka_worker_heartbeat_interval_sec: int = 10



class LoggingRetentionConfig(BaseModel):
    """日志保留配置。"""

    info_days: int = 7
    error_days: int = 30
    debug_days: int = 3


class LoggingConfig(BaseModel):
    """日志配置。"""

    console_level: str = "DEBUG"
    log_dir: str = "logs"
    retention: LoggingRetentionConfig = Field(default_factory=LoggingRetentionConfig)

    # ====== 新增：结构化日志 ======
    json_format: bool = True
    """文件日志使用 JSON Lines 格式输出。"""

    enable_compress: bool = True
    """轮转日志文件自动 .gz 压缩。"""

    trace_enabled: bool = True
    """启用全链路追踪（request_id / trace_id）。"""

    slow_query_threshold_ms: int = 200
    """慢查询阈值（毫秒，预留字段）。"""

    module_levels: dict[str, str] = Field(default_factory=dict)
    """按模块路径独立控制日志级别，如 {"app.modules.auth": "WARNING"}。"""


# =============================================================================
# 主配置类
# =============================================================================
class RedisConfig(BaseModel):
    """Redis 配置。"""

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


class Settings(BaseModel):
    """应用统一配置。"""

    app: AppConfig = Field(default_factory=AppConfig)
    mongodb: MongoDBConfig = Field(default_factory=MongoDBConfig)
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


# =============================================================================
# 配置加载
# =============================================================================
def load_yaml_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """从 YAML 文件加载配置。

    Args:
        config_path: 配置文件路径，默认从环境变量或默认位置查找

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析错误
    """
    if config_path is None:
        config_path = get_config_path()
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            f"请复制 config.yaml.example 为 config.yaml 并修改配置"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    """获取应用配置单例。

    环境变量 `DML_APP_PORT` 会覆盖 config.yaml 中的 `app.port`，
    确保 server.sh 启动的端口与代码内读取的端口一致。

    Returns:
        Settings: 应用配置实例
    """
    config_data = load_yaml_config()

    # 环境变量 DML_APP_PORT 优先级高于配置文件，确保启动脚本与代码一致
    env_port = os.getenv("DML_APP_PORT")
    if env_port is not None:
        app_config = config_data.get("app", {})
        app_config["port"] = int(env_port)
        config_data["app"] = app_config

    return Settings(**config_data)


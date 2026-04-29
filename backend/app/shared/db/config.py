"""MongoDB 和应用基础配置。

配置从 config.yaml 统一加载，参考 app/shared/config/settings.py
"""

from app.shared.config import get_settings

# 获取统一配置
_settings = get_settings()

# MongoDB 配置（兼容旧接口）
MONGO_URI: str = _settings.mongodb.uri
MONGO_DB_NAME: str = _settings.mongodb.db_name

# 应用配置
APP_DEBUG: bool = _settings.app.debug
CORS_ORIGINS: list[str] = _settings.app.cors_origins

# JWT 配置
JWT_SECRET_KEY: str = _settings.jwt.secret_key
JWT_ALGORITHM: str = _settings.jwt.algorithm
JWT_EXPIRE_MINUTES: int = _settings.jwt.expire_minutes
JWT_ISSUER: str = _settings.jwt.issuer
JWT_AUDIENCE: str = _settings.jwt.audience

# 执行任务配置
EXECUTION_DISPATCH_MODE: str = _settings.execution.dispatch_mode
EXECUTION_AGENT_DISPATCH_PATH: str = _settings.execution.agent_dispatch_path
EXECUTION_HTTP_TIMEOUT_SEC: int = _settings.execution.http_timeout_sec
EXECUTION_SCHEDULER_INTERVAL_SEC: int = _settings.execution.scheduler_interval_sec
EXECUTION_KAFKA_WORKER_AGENT_ID: str = _settings.execution.kafka_worker_agent_id
EXECUTION_KAFKA_WORKER_HEARTBEAT_TTL_SEC: int = _settings.execution.kafka_worker_heartbeat_ttl_sec
EXECUTION_KAFKA_WORKER_HEARTBEAT_INTERVAL_SEC: int = _settings.execution.kafka_worker_heartbeat_interval_sec

# 终端配置
TERMINAL_SHELL: str = _settings.terminal.shell
TERMINAL_WORKDIR: str = _settings.terminal.workdir
TERMINAL_IDLE_TIMEOUT_SEC: int = _settings.terminal.idle_timeout_sec
TERMINAL_MAX_SESSIONS_PER_USER: int = _settings.terminal.max_sessions_per_user

# 日志配置
LOG_CONSOLE_LEVEL: str = _settings.logging.console_level
LOG_DIR: str = _settings.logging.log_dir
LOG_RETENTION_INFO_DAYS: int = _settings.logging.retention.info_days
LOG_RETENTION_ERROR_DAYS: int = _settings.logging.retention.error_days
LOG_RETENTION_DEBUG_DAYS: int = _settings.logging.retention.debug_days


# 保留旧接口兼容性
class Settings:
    """旧版 Settings 类兼容（已废弃，请使用 app.shared.config.get_settings）"""

    APP_DEBUG = APP_DEBUG
    MONGO_URI = MONGO_URI
    MONGO_DB_NAME = MONGO_DB_NAME
    CORS_ORIGINS = CORS_ORIGINS
    JWT_SECRET_KEY = JWT_SECRET_KEY
    JWT_ALGORITHM = JWT_ALGORITHM
    JWT_EXPIRE_MINUTES = JWT_EXPIRE_MINUTES
    JWT_ISSUER = JWT_ISSUER
    JWT_AUDIENCE = JWT_AUDIENCE
    EXECUTION_DISPATCH_MODE = EXECUTION_DISPATCH_MODE
    EXECUTION_AGENT_DISPATCH_PATH = EXECUTION_AGENT_DISPATCH_PATH
    EXECUTION_HTTP_TIMEOUT_SEC = EXECUTION_HTTP_TIMEOUT_SEC
    EXECUTION_SCHEDULER_INTERVAL_SEC = EXECUTION_SCHEDULER_INTERVAL_SEC
    EXECUTION_KAFKA_WORKER_AGENT_ID = EXECUTION_KAFKA_WORKER_AGENT_ID
    EXECUTION_KAFKA_WORKER_HEARTBEAT_TTL_SEC = EXECUTION_KAFKA_WORKER_HEARTBEAT_TTL_SEC
    EXECUTION_KAFKA_WORKER_HEARTBEAT_INTERVAL_SEC = EXECUTION_KAFKA_WORKER_HEARTBEAT_INTERVAL_SEC
    TERMINAL_SHELL = TERMINAL_SHELL
    TERMINAL_WORKDIR = TERMINAL_WORKDIR
    TERMINAL_IDLE_TIMEOUT_SEC = TERMINAL_IDLE_TIMEOUT_SEC
    TERMINAL_MAX_SESSIONS_PER_USER = TERMINAL_MAX_SESSIONS_PER_USER


settings = Settings()
"""配置代理模块

将扁平属性访问（settings.MONGO_URI）转发到统一配置（get_settings()）。
新代码请直接使用 from app.shared.config import get_settings。
"""

from app.shared.config import get_settings, Settings as _Settings


class _SettingsProxy:
    """扁平属性代理，兼容 settings.MONGO_URI 等旧式访问。

    属性映射到 get_settings() 对应的子配置字段，如：
    - settings.MONGO_URI → _settings.mongodb.uri
    - settings.JWT_SECRET_KEY → _settings.jwt.secret_key
    """

    _MAP: dict[str, tuple[str, str]] = {
        "APP_DEBUG": ("app", "debug"),
        "MONGO_URI": ("mongodb", "uri"),
        "MONGO_DB_NAME": ("mongodb", "db_name"),
        "CORS_ORIGINS": ("app", "cors_origins"),
        "JWT_SECRET_KEY": ("jwt", "secret_key"),
        "JWT_ALGORITHM": ("jwt", "algorithm"),
        "JWT_EXPIRE_MINUTES": ("jwt", "expire_minutes"),
        "JWT_ISSUER": ("jwt", "issuer"),
        "JWT_AUDIENCE": ("jwt", "audience"),
        "EXECUTION_SCHEDULER_INTERVAL_SEC": ("execution", "scheduler_interval_sec"),
        "EXECUTION_KAFKA_WORKER_AGENT_ID": ("execution", "kafka_worker_agent_id"),
        "EXECUTION_KAFKA_WORKER_HEARTBEAT_TTL_SEC": ("execution", "kafka_worker_heartbeat_ttl_sec"),
        "EXECUTION_KAFKA_WORKER_HEARTBEAT_INTERVAL_SEC": ("execution", "kafka_worker_heartbeat_interval_sec"),
    }

    def __getattr__(self, name: str):
        mapping = self._MAP.get(name)
        if mapping:
            section, field = mapping
            return getattr(getattr(get_settings(), section), field)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


settings = _SettingsProxy()

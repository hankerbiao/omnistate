from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_DEBUG: bool = False

    # MongoDB 配置
    MONGO_URI: str = "mongodb://10.17.154.252:27019?replicaSet=rs0"
    MONGO_DB_NAME: str = "workflow_db"

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]  # 建议在 .env 中覆盖此值，例如 ["http://localhost:3000"]

    # JWT 配置（RBAC 鉴权使用）
    JWT_SECRET_KEY: str = "59e5690ab844cdd1a137ec9c2486a0359fc5675a14296f3f9e9a842f87ef13b4"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 8
    JWT_ISSUER: str = "tcm-backend"
    JWT_AUDIENCE: str = "tcm-frontend"

    # 执行任务分发配置
    EXECUTION_DISPATCH_MODE: str = "rabbitmq"  # rabbitmq | http
    EXECUTION_AGENT_DISPATCH_PATH: str = "/api/v1/tasks"
    EXECUTION_HTTP_TIMEOUT_SEC: int = 10
    EXECUTION_SCHEDULER_INTERVAL_SEC: int = 60
    EXECUTION_KAFKA_WORKER_AGENT_ID: str = "execution-kafka-worker"
    EXECUTION_KAFKA_WORKER_HEARTBEAT_TTL_SEC: int = 30
    EXECUTION_KAFKA_WORKER_HEARTBEAT_INTERVAL_SEC: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

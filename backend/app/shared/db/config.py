from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MongoDB 配置
    MONGO_URI: str = "mongodb://10.17.154.252:27018"
    MONGO_DB_NAME: str = "workflow_db"

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]  # 建议在 .env 中覆盖此值，例如 ["http://localhost:3000"]

    # JWT 配置（RBAC 鉴权使用）
    JWT_SECRET_KEY: str = "CHANGE_ME_TO_SECURE_RANDOM"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 8
    JWT_ISSUER: str = "tcm-backend"
    JWT_AUDIENCE: str = "tcm-frontend"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

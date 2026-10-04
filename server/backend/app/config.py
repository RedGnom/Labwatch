"""Настройки сервера, читаются из .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "INFO"

    postgres_user: str = "labwatch"
    postgres_password: str = "labwatch"
    postgres_db: str = "labwatch"
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str = (
        "postgresql+psycopg://labwatch:labwatch@db:5432/labwatch"
    )

    node_token: str = "dev-node-token-please-change"


settings = Settings()
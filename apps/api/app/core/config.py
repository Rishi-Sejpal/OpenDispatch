"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Top-level settings for the OpenDispatch API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: str = Field(
        default="postgresql+psycopg://opendispatch:opendispatch@db:5432/opendispatch"
    )
    redis_url: str = Field(default="redis://redis:6379/0")

    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 3600
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 30

    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    api_public_url: str = "http://localhost:8000"
    web_public_url: str = "http://localhost:5173"

    storage_backend: Literal["local"] = "local"
    storage_local_path: str = "/var/opendispatch/storage"

    seed_user_email: str = "dispatch@opendispatch.example.com"
    seed_user_password: str = "dispatch123!"
    seed_user_name: str = "Dispatch Operator"

    calculation_engine_version: str = "1.0.0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

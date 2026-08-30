"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        # SQLAlchemy 2.x resolves a bare ``postgresql://`` URL to the legacy
        # psycopg2 driver, which is not installed in our image. Normalize
        # anything that points at PostgreSQL without an explicit driver to
        # the bundled psycopg (v3) driver so the app can connect.
        if not value:
            return value
        if value.startswith("postgres://"):
            value = "postgresql" + value[len("postgres"):]
        if value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    # Legacy JWT settings are retained for backwards compatibility with any
    # tools that still emit locally-signed tokens. All current authentication
    # goes through Supabase (see supabase_* below).
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 3600
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 30

    # Supabase. Required at runtime; placeholders below are safe defaults so
    # the process can boot, but every request that needs the database or auth
    # verification will fail until these are set to real values.
    supabase_url: str = "https://[YOUR-PROJECT-REF].supabase.co"
    supabase_anon_key: str = "[YOUR-SUPABASE-ANON-KEY]"
    supabase_service_role_key: str = "[YOUR-SUPABASE-SERVICE-ROLE-KEY]"
    supabase_jwt_secret: str = "[YOUR-SUPABASE-JWT-SECRET]"

    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    api_public_url: str = "http://localhost:8000"
    web_public_url: str = "http://localhost:5173"

    storage_backend: Literal["local"] = "local"
    storage_local_path: str = "/var/opendispatch/storage"

    seed_user_email: str = "dispatch@opendispatch.example.com"
    seed_user_password: str = "dispatch123!"
    seed_user_name: str = "Dispatch Operator"
    # Set to true when running the seed against a real Supabase project so the
    # default user is created via auth.admin.create_user. When false the seed
    # creates a local stub row only (useful for CI and local dev without
    # Supabase).
    seed_use_supabase_auth: bool = False

    calculation_engine_version: str = "1.0.0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_configured(self) -> bool:
        placeholders = ("[YOUR-", "change-me")
        return not any(
            s.startswith(placeholders)
            for s in (
                self.supabase_url,
                self.supabase_anon_key,
                self.supabase_service_role_key,
                self.supabase_jwt_secret,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

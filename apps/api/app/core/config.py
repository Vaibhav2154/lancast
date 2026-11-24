from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (DEP-07)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "LANCAST API"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production", "test"] = "development"
    deployment_profile: Literal["standalone", "central"] = "standalone"
    public_base_url: str = "http://localhost"

    # Authoritative database (local PostgreSQL default; optional external PostgreSQL URL)
    database_url: str = "postgresql+asyncpg://lancast:lancast@postgres:5432/lancast"
    redis_url: str = "redis://redis:6379/0"

    # Local FastAPI auth configuration (never commit real production secrets)
    auth_secret_key: str = Field(default="dev-only-change-me-in-production", min_length=16)
    session_ttl_minutes: int = Field(default=480, ge=5, le=1440)

    # Observability & safety bounds
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    execution_queue_max_depth: int = Field(default=500, ge=1, le=100000)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        allowed = ("postgresql://", "postgresql+asyncpg://", "postgresql+psycopg://")
        if not value.startswith(allowed):
            raise ValueError("database_url must be a PostgreSQL connection URL")
        return value

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous psycopg URL for Alembic migrations."""
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()

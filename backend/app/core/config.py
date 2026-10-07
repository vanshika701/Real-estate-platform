from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"  # noqa: S105


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env file)."""

    # Reads the repo-root .env when run from backend/; real env vars always take precedence.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://propvisit:propvisit@localhost:5432/propvisit"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = DEV_JWT_SECRET
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # NoDecode lets us accept a plain comma-separated string instead of JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    cache_enabled: bool = True

    # Optional third-party services; local fallbacks are used when these are unset.
    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_bucket: str = "listing-images"
    resend_api_key: str | None = None
    email_from: str = "PropVisit <noreply@propvisit.dev>"

    @model_validator(mode="before")
    @classmethod
    def _split_cors_origins(cls, data: dict[str, object]) -> dict[str, object]:
        raw = data.get("cors_origins")
        if isinstance(raw, str):
            data["cors_origins"] = [o.strip() for o in raw.split(",") if o.strip()]
        return data

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

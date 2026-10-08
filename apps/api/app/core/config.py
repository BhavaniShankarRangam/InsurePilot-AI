from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=API_ROOT / ".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "InsurePilot AI"
    secret_key: str = "dev-only-insecure-secret-change-me-0123456789"
    field_encryption_key: str = ""
    access_token_minutes: int = 60
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    session_cookie_name: str = "ip_session"

    database_url: str = f"sqlite:///{(API_ROOT / 'data' / 'insurepilot.db').as_posix()}"
    redis_url: str = ""
    celery_broker_url: str = ""
    upload_dir: Path = API_ROOT / "data" / "uploads"
    max_upload_mb: int = 20

    llm_provider: Literal["mock", "anthropic", "openai", "gemini"] = "mock"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_model_large: str = ""
    llm_model_small: str = ""
    anthropic_enable_fallbacks: bool = True
    embedding_provider: Literal["local", "openai"] = "local"
    embedding_dim: int = 384

    langsmith_api_key: str = ""
    langsmith_project: str = "insurepilot"
    log_level: str = "INFO"

    rate_limit_per_minute: int = 120
    ai_rate_limit_per_minute: int = 30

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.secret_key.startswith("dev-only"):
        raise RuntimeError("SECRET_KEY must be set in production")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings

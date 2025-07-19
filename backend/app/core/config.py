from typing import Any, Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    if isinstance(v, list):
        return v
    raise ValueError(f"Invalid CORS origins: {v!r}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Core App Info
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.1.0"
    PROJECT_NAME: str = "AI Codebase Backend"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # Secrets & Expiry
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # PostgreSQL & Redis
    DATABASE_URL: str
    REDIS_URL: str

    # CORS
    FRONTEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # GitHub OAuth
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: AnyHttpUrl
    GITHUB_AUTHORIZE_URL: AnyHttpUrl = "https://github.com/login/oauth/authorize"
    GITHUB_ACCESS_TOKEN_URL: AnyHttpUrl = "https://github.com/login/oauth/access_token"
    GITHUB_API_BASE_URL: AnyHttpUrl = "https://api.github.com/"

    # AI / VectorDB
    OPENAI_API_KEY: str
    CHROMA_DB_URL: AnyHttpUrl

    # External Server
    SERVER_HOST: AnyHttpUrl

    # OTLP Exporters
    OTLP_TRACES_URL: AnyHttpUrl = "http://tempo:4318/v1/traces"
    OTLP_METRICS_URL: AnyHttpUrl = "http://mimir:4318/v1/metrics"
    OTLP_LOGS_URL: AnyHttpUrl = "http://loki:4318/v1/logs"

    @field_validator("FRONTEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _normalize_cors(cls, v: Any) -> list[str]:
        return parse_cors(v)


settings = Settings()

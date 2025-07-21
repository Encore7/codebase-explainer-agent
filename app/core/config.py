from typing import Any, Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str]:
    """Parse CORS origins from a string or list.
    If a string is provided, it splits by commas and trims whitespace.
    If a list is provided, it returns the list as is.
    Raises ValueError if the input is invalid.
    """
    try:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS origins: {v!r}")
    except Exception as exc:
        raise ValueError(f"Failed to parse CORS origins: {v!r}") from exc


class Settings(BaseSettings):
    """Application settings and configuration.
    This class uses Pydantic for settings management and validation.
    It loads environment variables from a .env file and provides type-safe access
    to application settings.
    Attributes:
        API_V1_STR (str): API version string.
        VERSION (str): Application version.
        PROJECT_NAME (str): Name of the project.
        ENVIRONMENT (Literal): Environment type (local, staging, production).
        JWT_ALGORITHM (str): JWT algorithm used for token signing.
        SECRET_KEY (str): Secret key for JWT signing.
        ACCESS_TOKEN_EXPIRE_MINUTES (int): Expiry time for access tokens in minutes.
        REFRESH_TOKEN_EXPIRE_MINUTES (int): Expiry time for refresh tokens in minutes.
        DATABASE_URL (str): PostgreSQL database connection URL.
        REDIS_URL (str): Redis connection URL.
        FRONTEND_CORS_ORIGINS (list[str]): List of allowed CORS origins.
        GITHUB_CLIENT_ID (str): GitHub OAuth client ID.
        GITHUB_CLIENT_SECRET (str): GitHub OAuth client secret.
        GITHUB_REDIRECT_URI (AnyHttpUrl): Redirect URI for GitHub OAuth.
        GITHUB_AUTHORIZE_URL (AnyHttpUrl): GitHub OAuth authorize URL.
        GITHUB_ACCESS_TOKEN_URL (AnyHttpUrl): GitHub OAuth access token URL.
        GITHUB_API_BASE_URL (AnyHttpUrl): Base URL for GitHub API.
        OPENAI_API_KEY (str): OpenAI API key for AI services.
        CHROMA_DB_URL (AnyHttpUrl): ChromaDB connection URL for vector database.
        SERVER_HOST (AnyHttpUrl): Host URL for the external server.
        OTLP_ENDPOINT (AnyHttpUrl): Endpoint for Grafana OTLP tracing.
        OTLP_TOKEN (str): Token for Grafana OTLP tracing authentication.
    Raises:
        ValueError: If any of the settings are invalid or cannot be parsed.
    """

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
    JWT_ALGORITHM: str = "HS256"
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

    # Grafana OTLP
    OTLP_ENDPOINT: AnyHttpUrl
    OTLP_TOKEN: str

    @field_validator("FRONTEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _normalize_cors(cls, v: Any) -> list[str]:
        return parse_cors(v)


settings = Settings()

"""
AuraFit — Configuration management (Stage 3: full auth system).
Single Settings class. All values from environment variables (12-factor app).
Validated at startup via Pydantic. Cached as singleton via @lru_cache.
No secrets in code or git. Use AWS Secrets Manager / GCP Secret Manager for
JWT keys, Google OAuth credentials, and DATABASE_URL in production.
"""
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL      = "local"
    STAGING    = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME:    str = "AuraFit User Service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.LOCAL
    DEBUG:       bool = False
    LOG_LEVEL:   str = "INFO"

    # ── Server ────────────────────────────────────────────────────────────────
    HOST:          str = "0.0.0.0"
    PORT:          int = 8001
    WORKERS:       int = 1
    API_V1_PREFIX: str = "/api/v1"

    # ── Security / JWT ────────────────────────────────────────────────────────
    SECRET_KEY:                   str = Field(..., min_length=32)
    ALGORITHM:                    str = "RS256"
    JWT_PRIVATE_KEY:              str = Field(...)   # PEM — from Secrets Manager
    JWT_PUBLIC_KEY:               str = Field(...)   # PEM — from Secrets Manager
    ACCESS_TOKEN_EXPIRE_MINUTES:  int = 15
    REFRESH_TOKEN_EXPIRE_DAYS:    int = 7

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL:          PostgresDsn = Field(...)
    DATABASE_POOL_SIZE:    int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO:         bool = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL:             RedisDsn = Field(...)
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT:  int = 5
    REDIS_CONNECT_TIMEOUT: int = 5

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL:        str  = Field(...)
    CELERY_RESULT_BACKEND:    str  = Field(...)
    CELERY_TASK_ALWAYS_EAGER: bool = False   # True in tests only

    # ── AWS / Storage ─────────────────────────────────────────────────────────
    AWS_REGION:            str = "us-east-1"
    AWS_ACCESS_KEY_ID:     str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_UPLOADS_BUCKET:     str = Field(...)
    S3_ASSETS_BUCKET:      str = Field(...)
    CDN_BASE_URL:          AnyHttpUrl = Field(...)
    PRESIGNED_URL_EXPIRE_SECONDS: int = 300

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5
    RATE_LIMIT_API_PER_MINUTE:  int = 60
    RATE_LIMIT_AI_PER_HOUR:     int = 30

    # ── Internal service URLs ─────────────────────────────────────────────────
    PRODUCT_SERVICE_URL:        AnyHttpUrl = Field(default="http://product-service:8002")
    RECOMMENDATION_SERVICE_URL: AnyHttpUrl = Field(default="http://recommendation-service:8003")
    AI_FACIAL_SERVICE_URL:      AnyHttpUrl = Field(default="http://ai-facial:8010")

    # ── Email (AWS SES) ───────────────────────────────────────────────────────
    SES_FROM_EMAIL: str = "noreply@aurafit.ai"
    SES_FROM_NAME:  str = "AuraFit"

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID:     str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI:  str = "http://localhost:3000/auth/callback"

    # ── Frontend URL (used in email links) ────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Token TTLs ────────────────────────────────────────────────────────────
    EMAIL_VERIFY_TOKEN_EXPIRE_HOURS:   int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1

    # ── MFA ───────────────────────────────────────────────────────────────────
    MFA_ISSUER: str = "AuraFit"

    # ── Feature flags ─────────────────────────────────────────────────────────
    FEATURE_FACIAL_SCAN:   bool = True
    FEATURE_VIRTUAL_TRYON: bool = True
    FEATURE_CHATBOT:       bool = True

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("DATABASE_ECHO", mode="before")
    @classmethod
    def never_echo_in_prod(cls, v: Any, info: Any) -> bool:
        if info.data.get("ENVIRONMENT") == Environment.PRODUCTION:
            return False
        return bool(v)

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if "dev-secret" in self.SECRET_KEY.lower():
                raise ValueError("SECRET_KEY must not be a dev placeholder in production")
        return self

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == Environment.LOCAL

    @property
    def database_url_str(self) -> str:
        """Return asyncpg-compatible DB URL string (FastAPI app)."""
        url = str(self.DATABASE_URL)
        return (
            url
            .replace("postgresql://", "postgresql+asyncpg://")
            .replace("postgres://",   "postgresql+asyncpg://")
        )

    @property
    def database_url_sync_str(self) -> str:
        """Return psycopg2-compatible DB URL string (Celery workers — sync)."""
        url = str(self.DATABASE_URL)
        return (
            url
            .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("postgresql://",          "postgresql+psycopg2://")
            .replace("postgres://",            "postgresql+psycopg2://")
        )


@lru_cache
def get_settings() -> Settings:
    """
    Cached Settings singleton.
    Use as FastAPI dependency: Depends(get_settings)
    Or call directly: get_settings()
    """
    return Settings()  # type: ignore[call-arg]

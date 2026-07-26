"""
AuraFit — Recommendation Service configuration.
All settings sourced from environment variables. Validated at startup.
"""
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, field_validator
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
    APP_NAME:    str = "AuraFit Recommendation Service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.LOCAL
    DEBUG:       bool = False
    LOG_LEVEL:   str = "INFO"

    # ── Server ────────────────────────────────────────────────────────────────
    HOST:          str = "0.0.0.0"
    PORT:          int = 8003
    WORKERS:       int = 2
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL:          PostgresDsn = Field(...)
    DATABASE_POOL_SIZE:    int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO:         bool = False

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL:             RedisDsn = Field(...)
    REDIS_MAX_CONNECTIONS: int = 50

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL:     str = Field(...)
    CELERY_RESULT_BACKEND: str = Field(...)

    # ── Algorithm tuning ──────────────────────────────────────────────────────
    # Hybrid weighting (must sum to 1.0)
    CF_WEIGHT:           float = 0.40   # Collaborative filtering
    CB_WEIGHT:           float = 0.40   # Content-based (embedding similarity)
    PROFILE_WEIGHT:      float = 0.20   # Profile-based rule score

    # Candidate pool sizes
    CF_CANDIDATES:       int = 300      # Max candidates from CF
    CB_CANDIDATES:       int = 200      # Max candidates from content-based
    FINAL_RESULTS:       int = 20       # Items returned to client

    # ALS model parameters
    ALS_FACTORS:         int = 128
    ALS_ITERATIONS:      int = 20
    ALS_REGULARIZATION:  float = 0.01
    ALS_ALPHA:           float = 40.0   # Confidence scaling for implicit feedback

    # Embedding
    EMBEDDING_MODEL:     str = "all-MiniLM-L6-v2"   # SBERT model
    EMBEDDING_DIM:       int = 384                    # Output dimension
    CLIP_EMBEDDING_DIM:  int = 512                    # CLIP ViT-B/32

    # Cache TTLs (seconds)
    CACHE_RECS_TTL:      int = 3600        # 1h: per-user recommendation cache
    CACHE_PRODUCT_TTL:   int = 1800        # 30m: product detail cache
    CACHE_CF_TTL:        int = 86400       # 24h: CF candidate sorted sets

    # Business rules
    MAX_ITEMS_PER_BRAND:  int = 3          # Diversity constraint
    NEW_PRODUCT_DAYS:     int = 14         # "new arrival" boost window
    NEW_PRODUCT_BOOST:    float = 1.05     # Score multiplier for new arrivals
    TRENDING_WINDOW_DAYS: int = 7
    MIN_INTERACTION_FOR_CF: int = 3        # Minimum interactions before using CF

    # Inter-service
    USER_SERVICE_URL:    AnyHttpUrl = Field(default="http://user-service:8001")

    @field_validator("DATABASE_ECHO", mode="before")
    @classmethod
    def no_echo_in_prod(cls, v: Any, info: Any) -> bool:
        if info.data.get("ENVIRONMENT") == Environment.PRODUCTION:
            return False
        return bool(v)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def database_url_str(self) -> str:
        url = str(self.DATABASE_URL)
        return url.replace("postgresql://", "postgresql+asyncpg://").replace(
            "postgres://", "postgresql+asyncpg://"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

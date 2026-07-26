"""
AuraFit — Virtual Try-On & Wardrobe AI Service configuration.
"""
from __future__ import annotations

from functools import lru_cache
from pydantic import AnyHttpUrl, Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    APP_NAME:    str = "AuraFit Virtual Try-On Service"
    APP_VERSION: str = "1.0.0"
    HOST:        str = "0.0.0.0"
    PORT:        int = 8020
    DEBUG:       bool = False

    # Redis
    REDIS_URL: RedisDsn = Field(...)

    # Celery
    CELERY_BROKER_URL:     str = Field(...)
    CELERY_RESULT_BACKEND: str = Field(...)

    # AWS
    AWS_REGION:            str = "us-east-1"
    AWS_ACCESS_KEY_ID:     str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_UPLOADS_BUCKET:     str = Field(...)
    CDN_BASE_URL:          AnyHttpUrl = Field(...)

    # Inter-service
    USER_SERVICE_URL: AnyHttpUrl = Field(default="http://user-service:8001")

    # Makeup AR parameters
    LIPSTICK_ALPHA_DEFAULT:   float = 0.55     # Blend opacity for lip colour
    FOUNDATION_ALPHA_DEFAULT: float = 0.30     # Foundation coverage level
    EYESHADOW_ALPHA_DEFAULT:  float = 0.50
    HAIR_ALPHA_DEFAULT:       float = 0.60

    # Wardrobe AI
    WARDROBE_CLASSIFICATION_MODEL: str = "microsoft/resnet-50"
    WARDROBE_CLIP_MODEL:           str = "openai/clip-vit-base-patch32"
    OUTFIT_GENERATION_LIMIT:       int = 5     # Max AI outfit suggestions per request
    CAPSULE_TARGET_SIZE:           int = 33    # Classic capsule wardrobe item count

    # Celebrity matching
    CELEBRITY_INDEX_PATH:   str = "/app/models/celebrity_faiss.index"
    CELEBRITY_META_PATH:    str = "/app/models/celebrity_meta.json"
    CELEBRITY_TOP_K:        int = 5
    CELEBRITY_EMBEDDING_DIM:int = 512          # CLIP ViT-B/32


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

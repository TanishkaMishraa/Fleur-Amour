"""
AuraFit AI Facial Analysis Service — Configuration.
Environment-driven. Validated at startup.
"""
from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SERVICE_NAME: str = "aurafit-facial-analysis"
    PORT:         int = 8010
    LOG_LEVEL:    str = "INFO"

    # ── S3 ─────────────────────────────────────────────────────────────────────
    AWS_REGION:           str = "us-east-1"
    AWS_ACCESS_KEY_ID:    str = ""
    AWS_SECRET_ACCESS_KEY:str = ""
    S3_UPLOADS_BUCKET:    str = Field(...)

    # ── Pipeline tuning ───────────────────────────────────────────────────────
    # Image preprocessing
    MAX_IMAGE_DIMENSION:   int = 1024   # px — resize before inference
    MIN_FACE_CONFIDENCE:   float = 0.7  # MediaPipe minimum detection confidence
    MIN_IMAGE_QUALITY:     float = 30.0 # BRISQUE: reject below this
    JPEG_QUALITY:          int = 92

    # Face mesh
    MEDIAPIPE_MODEL_COMPLEXITY: int = 1  # 0=fast, 1=balanced, 2=accurate
    MEDIAPIPE_REFINE_LANDMARKS: bool = True

    # DeepFace
    DEEPFACE_BACKEND:  str = "retinaface"  # retinaface | mtcnn | opencv
    DEEPFACE_MODEL:    str = "VGG-Face"    # embedding model
    DEEPFACE_ENFORCE_DETECTION: bool = False  # allow partial results

    # GPU
    USE_GPU: bool = False  # set True on GPU instances
    GPU_DEVICE: str = "0"  # CUDA device index

    # Caching
    MODEL_CACHE_DIR: str = "/tmp/aurafit-models"

    # Timeouts
    S3_DOWNLOAD_TIMEOUT: int = 30
    INFERENCE_TIMEOUT:   int = 90

    # Internal
    INTERNAL_SERVICE_KEY: str = Field(default="", description="Shared secret for internal calls")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

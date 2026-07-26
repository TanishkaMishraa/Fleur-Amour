"""
AuraFit AI Facial Analysis — API endpoints.
This service is INTERNAL ONLY (not exposed via Nginx to the public internet —
see Stage 0 AI Microservice Architecture). Called by:
  - user-service Celery workers (async path, /analyze)
  - user-service sync calls for lightweight checks (/health, /quality-check)

Endpoints:
  POST /analyze          — full pipeline, S3 key input (used by Celery tasks)
  POST /analyze/upload    — full pipeline, direct multipart upload (testing/debug)
  GET  /health            — liveness + model-loaded status
  GET  /ready              — readiness probe (models warmed up)
"""
from __future__ import annotations

import time

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.pipeline.orchestrator import get_pipeline
from app.schemas.analysis_schemas import (
    AnalyzeRequest,
    HealthResponse,
    SyncAnalyzeResponse,
)

router = APIRouter()
logger = get_logger(__name__)
_settings = get_settings()
_start_time = time.time()


@router.post(
    "/analyze",
    response_model=SyncAnalyzeResponse,
    summary="Run full facial analysis pipeline on an S3-stored image",
    description=(
        "Internal endpoint called by user-service Celery workers. "
        "Downloads the image from S3, runs the complete analysis pipeline "
        "(face detection, mesh, skin tone/undertone, face shape, age, hair, "
        "acne, dark circles, texture, symmetry), and returns the full result."
    ),
)
async def analyze(payload: AnalyzeRequest) -> SyncAnalyzeResponse:
    pipeline = get_pipeline()
    logger.info("analysis.start", task_id=payload.task_id, user_id=payload.user_id, s3_key=payload.s3_key)

    # CPU-bound pipeline — run in default executor to avoid blocking the event loop
    import asyncio
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, pipeline.run_from_s3, payload.s3_key, payload.task_id
    )

    if response.success:
        logger.info(
            "analysis.complete",
            task_id=payload.task_id,
            processing_time_ms=response.result.processing_time_ms if response.result else None,
        )
    else:
        logger.warning(
            "analysis.failed",
            task_id=payload.task_id,
            error_code=response.error.error_code if response.error else None,
            error_message=response.error.error_message if response.error else None,
        )

    return response


@router.post(
    "/analyze/upload",
    response_model=SyncAnalyzeResponse,
    summary="Run full facial analysis on a directly-uploaded image",
    description="Debug/testing endpoint — bypasses S3. Not used by production task flow.",
)
async def analyze_upload(file: UploadFile = File(...)) -> SyncAnalyzeResponse:
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File must be JPEG, PNG, or WebP",
        )

    data = await file.read()
    max_bytes = 10 * 1024 * 1024  # 10MB
    if len(data) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds 10MB limit")

    pipeline = get_pipeline()
    task_id = f"debug-{int(time.time() * 1000)}"

    import asyncio
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, pipeline.run_from_bytes, data, task_id)
    return response


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    gpu_available = False
    try:
        import tensorflow as tf
        gpu_available = len(tf.config.list_physical_devices("GPU")) > 0
    except Exception:
        pass

    model_loaded = True
    try:
        get_pipeline()
    except Exception:
        model_loaded = False

    return HealthResponse(
        status="ok",
        service=_settings.SERVICE_NAME,
        version="1.0.0",
        gpu_available=gpu_available,
        model_loaded=model_loaded,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@router.get("/ready", summary="Readiness probe — verifies pipeline is warmed up")
async def ready() -> dict:
    """
    Kubernetes readiness probe. Returns 503 until the MediaPipe/DeepFace
    models have been loaded into memory (first request would otherwise
    incur a multi-second cold-start penalty).
    """
    try:
        get_pipeline()
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

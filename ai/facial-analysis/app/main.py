"""
AuraFit AI Facial Analysis Service — FastAPI application factory.
Internal-only microservice (Stage 0 AI Microservice Architecture).
Not exposed via Nginx — called by user-service Celery workers over the
internal Docker/Kubernetes network only.

Startup pre-loads MediaPipe FaceMesh + DeepFace models so the first real
request doesn't pay the cold-start cost (model loading can take 3-8s).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.pipeline.orchestrator import get_pipeline, shutdown_pipeline

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger = get_logger(__name__)
    logger.info("aurafit.ai.startup.begin", service=settings.SERVICE_NAME)

    # Pre-load all models (MediaPipe FaceMesh, DeepFace age model) at startup.
    # This is the single most impactful latency optimisation for this service —
    # without it, the first request after a pod restart takes 3-8s longer.
    get_pipeline()
    logger.info("aurafit.ai.models_loaded")

    logger.info("aurafit.ai.startup.complete")
    yield

    logger.info("aurafit.ai.shutdown.begin")
    shutdown_pipeline()
    logger.info("aurafit.ai.shutdown.complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AuraFit AI Facial Analysis Service",
        version="1.0.0",
        description=(
            "Internal microservice: face detection, 468-point mesh, skin tone & "
            "undertone, face shape, age estimation, hair analysis, acne/dark circle "
            "detection, skin texture, and facial symmetry. "
            "Not exposed to the public internet — internal network only."
        ),
        docs_url="/docs",       # internal service — docs OK even outside local
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.include_router(api_router)

    return app


app = create_app()

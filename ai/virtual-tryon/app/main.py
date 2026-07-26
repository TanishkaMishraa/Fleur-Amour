"""
AuraFit — Virtual Try-On & Wardrobe AI Service (port 8020).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.endpoints import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load models at startup
    from app.services.celebrity.celebrity_engine import celebrity_engine
    celebrity_engine.load()

    from app.services.tryon.makeup_engine import _get_face_mesh
    _get_face_mesh()   # Warm up MediaPipe

    structlog.get_logger().info("vtryon.startup_complete")
    yield


def create_app() -> FastAPI:
    from app.core.config import get_settings
    s = get_settings()

    app = FastAPI(
        title=s.APP_NAME,
        version=s.APP_VERSION,
        description="AuraFit Virtual Try-On, Wardrobe AI, and Celebrity Matching",
        docs_url="/docs",
        lifespan=lifespan,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()

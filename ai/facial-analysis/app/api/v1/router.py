"""AuraFit AI Facial Analysis — API v1 router."""
from fastapi import APIRouter

from app.api.v1 import endpoints

api_router = APIRouter()
api_router.include_router(endpoints.router, tags=["Facial Analysis"])

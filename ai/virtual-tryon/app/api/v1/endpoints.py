"""
AuraFit — Virtual Try-On, Wardrobe AI, and Celebrity Matching API (Stage 9).

Routes:
  POST /tryon/makeup           — Apply lipstick/foundation/eyeshadow
  POST /tryon/hair             — Apply hair colour simulation
  POST /wardrobe/classify      — Classify a clothing item image
  POST /wardrobe/outfits       — Generate outfit combinations
  POST /wardrobe/capsule       — Analyse wardrobe for capsule completeness
  POST /celebrity/match        — Find similar celebrity style matches

  GET  /health                 — Service health probe
"""
from __future__ import annotations

import time
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.logging import get_logger
from app.services.tryon.makeup_engine import MakeupAREngine, TryOnRequest, TryOnType, makeup_engine
from app.services.wardrobe.wardrobe_engine import wardrobe_engine
from app.services.celebrity.celebrity_engine import celebrity_engine

logger = get_logger(__name__)
router = APIRouter()


# ── Request / response schemas ────────────────────────────────────────────────

class TryOnResponse(BaseModel):
    success:       bool
    try_on_type:   str
    applied_hex:   str
    result_url:    str | None = None      # S3 URL of result (production)
    result_b64:    str | None = None      # Base64-encoded result (dev/direct)
    processing_ms: int
    face_detected: bool
    error:         str | None = None


class WardrobeClassifyResponse(BaseModel):
    success:         bool
    category:        str
    subcategory:     str
    confidence:      float
    dominant_colors: list[str]
    occasion_tags:   list[str]
    season_tags:     list[str]
    style_tags:      list[str]


class OutfitSuggestionOut(BaseModel):
    outfit_id:     str
    items:         list[dict]
    occasion:      str
    season:        str
    color_harmony: str
    ai_score:      float
    explanation:   str
    style_tags:    list[str]


class OutfitGenerateRequest(BaseModel):
    wardrobe_items: list[dict]           # [{id, category, image_url, color_tags, ...}]
    occasion:       str | None = None
    season:         str | None = None
    color_season:   str | None = None
    archetype:      str | None = None
    limit:          int = 5


class CapsuleRequest(BaseModel):
    wardrobe_items: list[dict]
    archetype:      str | None = None


class CapsuleResponse(BaseModel):
    total_items:       int
    total_value:       float
    category_counts:   dict[str, int]
    missing_essentials:list[dict]
    redundancies:      list[dict]
    cost_per_wear:     list[dict]
    capsule_score:     float
    shopping_list:     list[dict]


class CelebrityMatchOut(BaseModel):
    name:              str
    similarity_score:  float
    similarity_pct:    int
    style_archetypes:  list[str]
    known_aesthetics:  list[str]
    makeup_signature:  str
    fashion_signature: str
    fragrance_family:  str | None
    style_tip:         str
    inspiration_tags:  list[str]


class CelebrityMatchResponse(BaseModel):
    matches:         list[CelebrityMatchOut]
    query_aesthetic: str
    style_era:       str
    primary_style:   str


# ── Virtual Try-On endpoints ──────────────────────────────────────────────────

@router.post(
    "/tryon/makeup",
    response_model=TryOnResponse,
    summary="Apply virtual makeup to a selfie",
    description=(
        "Server-side makeup AR using MediaPipe FaceMesh + OpenCV. "
        "Supports lipstick, foundation, and eyeshadow simulation. "
        "Returns result as base64 JPEG (development) or S3 URL (production)."
    ),
)
async def tryon_makeup(
    file:       UploadFile   = File(...,    description="Selfie image (JPEG or PNG)"),
    hex_color:  str          = Form(...,    description="Hex colour code e.g. #C41E3A"),
    try_on_type:str          = Form(...,    description="lipstick | foundation | eyeshadow"),
    intensity:  float        = Form(1.0,   description="Effect intensity 0.0–1.0"),
) -> TryOnResponse:
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, or WebP images accepted")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be < 10MB")

    try:
        tryon_type_enum = TryOnType(try_on_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid try_on_type. Valid: {[t.value for t in TryOnType if t != TryOnType.HAIR_COLOR]}"
        )

    req    = TryOnRequest(
        image_bytes=image_bytes,
        hex_color=hex_color.lstrip("#").join(["#", ""]).replace("##", "#"),
        try_on_type=tryon_type_enum,
        intensity=max(0.0, min(1.0, intensity)),
    )
    result = makeup_engine.try_on(req)

    # In production: upload to S3 and return URL.
    # Here: return base64-encoded image for direct rendering.
    import base64
    b64 = base64.b64encode(result.result_bytes).decode() if result.success else None

    return TryOnResponse(
        success=result.success,
        try_on_type=result.try_on_type,
        applied_hex=result.applied_hex,
        result_b64=b64,
        processing_ms=result.processing_ms,
        face_detected=result.face_detected,
        error=result.error,
    )


@router.post(
    "/tryon/hair",
    response_model=TryOnResponse,
    summary="Apply virtual hair colour simulation",
)
async def tryon_hair(
    file:      UploadFile = File(...),
    hex_color: str        = Form(...),
    intensity: float      = Form(1.0),
) -> TryOnResponse:
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP accepted")

    image_bytes = await file.read()
    req    = TryOnRequest(
        image_bytes=image_bytes,
        hex_color=hex_color,
        try_on_type=TryOnType.HAIR_COLOR,
        intensity=max(0.0, min(1.0, intensity)),
    )
    result = makeup_engine.try_on(req)

    import base64
    b64 = base64.b64encode(result.result_bytes).decode() if result.success else None
    return TryOnResponse(
        success=result.success,
        try_on_type=result.try_on_type,
        applied_hex=result.applied_hex,
        result_b64=b64,
        processing_ms=result.processing_ms,
        face_detected=result.face_detected,
        error=result.error,
    )


# ── Wardrobe AI endpoints ─────────────────────────────────────────────────────

@router.post(
    "/wardrobe/classify",
    response_model=WardrobeClassifyResponse,
    summary="Classify a clothing item image",
    description=(
        "Uses CLIP zero-shot classification to categorise the item "
        "(tops/bottoms/dresses/shoes/bags/outerwear/accessories), "
        "extract dominant colours, and assign occasion/season/style tags."
    ),
)
async def classify_item(
    file: UploadFile = File(..., description="Clothing item image"),
) -> WardrobeClassifyResponse:
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP accepted")

    image_bytes = await file.read()
    result = wardrobe_engine.classify_item(image_bytes)

    return WardrobeClassifyResponse(
        success=True,
        category=result.category,
        subcategory=result.subcategory,
        confidence=result.confidence,
        dominant_colors=result.dominant_colors,
        occasion_tags=result.occasion_tags,
        season_tags=result.season_tags,
        style_tags=result.style_tags,
    )


@router.post(
    "/wardrobe/outfits",
    response_model=list[OutfitSuggestionOut],
    summary="Generate AI outfit combinations",
    description=(
        "Given the user's wardrobe items (with categories, colours, tags), "
        "generates N outfit combinations using colour harmony rules and "
        "occasion/season filters. Each outfit gets an AI explanation."
    ),
)
async def generate_outfits(payload: OutfitGenerateRequest) -> list[OutfitSuggestionOut]:
    suggestions = wardrobe_engine.generate_outfits(
        wardrobe_items=payload.wardrobe_items,
        occasion=payload.occasion,
        season=payload.season,
        color_season=payload.color_season,
        archetype=payload.archetype,
        limit=payload.limit,
    )
    return [
        OutfitSuggestionOut(
            outfit_id=s.outfit_id,
            items=s.items,
            occasion=s.occasion,
            season=s.season,
            color_harmony=s.color_harmony,
            ai_score=s.ai_score,
            explanation=s.explanation,
            style_tags=s.style_tags,
        )
        for s in suggestions
    ]


@router.post(
    "/wardrobe/capsule",
    response_model=CapsuleResponse,
    summary="Analyse wardrobe for capsule completeness",
    description=(
        "Returns a full capsule wardrobe analysis: missing essentials, "
        "redundant items, cost-per-wear, and a prioritised shopping list."
    ),
)
async def analyse_capsule(payload: CapsuleRequest) -> CapsuleResponse:
    analysis = wardrobe_engine.analyse_capsule(
        wardrobe_items=payload.wardrobe_items,
        archetype=payload.archetype,
    )
    return CapsuleResponse(
        total_items=analysis.total_items,
        total_value=analysis.total_value,
        category_counts=analysis.category_counts,
        missing_essentials=analysis.missing_essentials,
        redundancies=analysis.redundancies,
        cost_per_wear=analysis.cost_per_wear,
        capsule_score=analysis.capsule_score,
        shopping_list=analysis.shopping_list,
    )


# ── Celebrity Matching endpoints ──────────────────────────────────────────────

@router.post(
    "/celebrity/match",
    response_model=CelebrityMatchResponse,
    summary="Find celebrity style matches",
    description=(
        "Finds celebrity style inspirations similar to the uploaded selfie "
        "using CLIP image embeddings + FAISS ANN search. Returns top-5 "
        "celebrity matches with style, makeup, and fragrance guidance.\n\n"
        "Note: This uses semantic image similarity (CLIP), not face-recognition. "
        "Matches are style-based, not identity-based."
    ),
)
async def celebrity_match(
    file: UploadFile = File(..., description="Selfie image for style matching"),
) -> CelebrityMatchResponse:
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=415, detail="Only JPEG/PNG/WebP accepted")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be < 10MB")

    result = celebrity_engine.match(image_bytes)

    return CelebrityMatchResponse(
        matches=[
            CelebrityMatchOut(
                name=m.name,
                similarity_score=m.similarity_score,
                similarity_pct=m.similarity_pct,
                style_archetypes=m.style_archetypes,
                known_aesthetics=m.known_aesthetics,
                makeup_signature=m.makeup_signature,
                fashion_signature=m.fashion_signature,
                fragrance_family=m.fragrance_family,
                style_tip=m.style_tip,
                inspiration_tags=m.inspiration_tags,
            )
            for m in result.matches
        ],
        query_aesthetic=result.query_aesthetic,
        style_era=result.style_era,
        primary_style=result.primary_style,
    )


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["Health"])
async def health() -> dict:
    return {
        "status":           "ok",
        "service":          "AuraFit Virtual Try-On & Wardrobe AI",
        "version":          "1.0.0",
        "celebrity_index":  celebrity_engine._faiss_index is not None,
        "wardrobe_clip":    wardrobe_engine._clip_model is not None,
    }


@router.get("/ready", include_in_schema=False)
async def ready() -> dict:
    return {"status": "ready"}

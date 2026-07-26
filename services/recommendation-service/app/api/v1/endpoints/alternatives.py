"""
AuraFit — Smart Alternative Engine API endpoints.

Routes:
  GET  /alternatives/{product_id}         — get smart alternatives for a product
  POST /alternatives/compare/shade        — compare two hex shade codes
  POST /alternatives/compare/ingredients  — compare two ingredient lists
  POST /alternatives/compare/fragrance    — compare two fragrance attribute dicts
  POST /alternatives/trigger/{product_id} — trigger on-demand precompute (admin)

All endpoints are public (no JWT required) for product discovery.
Authenticated context can be added later for personalised ranking.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.alternative_schemas import (
    AlternativeGroupResponse,
    FragranceCompareRequest,
    IngredientCompareRequest,
    ShadeCompareRequest,
)
from app.services.alternatives.alternative_service import SmartAlternativeService
from app.services.alternatives.fragrance_engine import fragrance_engine
from app.services.alternatives.ingredient_engine import ingredient_engine
from app.services.alternatives.shade_engine import shade_engine

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

router = APIRouter(prefix="/alternatives", tags=["Smart Alternatives"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ── Main alternative endpoint ─────────────────────────────────────────────────

@router.get(
    "/{product_id}",
    response_model=AlternativeGroupResponse,
    summary="Get smart affordable alternatives for a product",
    description=(
        "Returns up to 10 affordable alternatives ranked by composite similarity. "
        "Each alternative includes sub-scores for embedding similarity, ingredient "
        "overlap, shade match (ΔE), fragrance note match, price savings, and a "
        "'Best Value' badge for the best score/price combination.\n\n"
        "Triggered automatically when a recommended product price exceeds ₹10,000."
    ),
)
async def get_alternatives(
    product_id:     UUID,
    session:        DbSession,
    limit:          int   = Query(default=5,    ge=1,  le=10),
    min_similarity: float = Query(default=0.40, ge=0.0, le=1.0),
) -> AlternativeGroupResponse:
    svc = SmartAlternativeService(session)
    return await svc.get_alternatives(
        source_id=product_id,
        limit=limit,
        min_similarity=min_similarity,
    )


# ── Direct comparison utilities (used by frontend detail view) ────────────────

@router.post(
    "/compare/shade",
    summary="Compare two hex shade codes",
    description=(
        "Converts both hex codes to CIELAB and computes ΔE (CIE 1994). "
        "Returns ΔE value, similarity %, and perceptual strength label."
    ),
)
async def compare_shades(payload: ShadeCompareRequest) -> dict:
    result = shade_engine.compare_hex(payload.hex_a, payload.hex_b)
    return {
        "delta_e":         result.delta_e,
        "similarity_pct":  result.similarity_pct,
        "similarity_score":result.similarity_score,
        "strength":        result.strength,
        "description":     result.description,
        "hex_a":           payload.hex_a,
        "hex_b":           payload.hex_b,
        "lab_a":           list(result.lab_source),
        "lab_b":           list(result.lab_alternative),
    }


@router.post(
    "/compare/ingredients",
    summary="Compare two INCI ingredient lists",
    description=(
        "Parses both ingredient strings, computes Jaccard + weighted active "
        "ingredient similarity. Returns matched active ingredients and formula strength."
    ),
)
async def compare_ingredients(payload: IngredientCompareRequest) -> dict:
    result = ingredient_engine.compare_raw(payload.ingredients_a, payload.ingredients_b)
    return {
        "jaccard_score":       result.jaccard_score,
        "weighted_score":      result.weighted_score,
        "similarity_pct":      round(result.weighted_score * 100),
        "strength":            result.strength,
        "key_matches":         result.key_matches,
        "active_match_count":  result.active_match_count,
        "total_actives_union": result.total_actives_union,
    }


@router.post(
    "/compare/fragrance",
    summary="Compare two fragrance note profiles",
    description=(
        "Compares top/mid/base note pyramids + olfactive family affinity. "
        "Returns note-level overlap and overall fragrance similarity."
    ),
)
async def compare_fragrance(payload: FragranceCompareRequest) -> dict:
    result = fragrance_engine.compare_attrs(payload.attrs_a, payload.attrs_b)
    return {
        "overall_score":   result.overall_score,
        "similarity_pct":  round(result.overall_score * 100),
        "note_score":      result.note_score,
        "family_score":    result.family_score,
        "character_score": result.character_score,
        "top_overlap":     result.top_overlap,
        "mid_overlap":     result.mid_overlap,
        "base_overlap":    result.base_overlap,
        "all_overlap":     result.all_overlap,
        "shared_family":   result.shared_family,
        "strength":        result.strength,
        "summary":         result.summary,
    }


# ── Admin: trigger precompute ─────────────────────────────────────────────────

@router.post(
    "/trigger/{product_id}",
    summary="Trigger on-demand alternative precomputation",
    description="Recomputes and caches alternatives for a specific product. Admin use.",
    include_in_schema=False,   # Hidden from public docs
)
async def trigger_precompute(product_id: UUID, session: DbSession) -> dict:
    svc = SmartAlternativeService(session)
    count = await svc.precompute_for_product(product_id)
    return {"status": "ok", "alternatives_stored": count, "product_id": str(product_id)}

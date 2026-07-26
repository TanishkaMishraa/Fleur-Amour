"""
AuraFit — Color Intelligence endpoints (/api/v1/color/*).

All endpoints are synchronous from the client's perspective — the engine
runs inline (~5ms) so no Celery task is needed.

Routes:
  POST /color/compute          — derive color profile from latest (or specified) scan
  GET  /color/profile          — get current active color profile
  GET  /color/history          — list all past color profiles
  DELETE /color/profiles/{id}  — remove a specific profile
  GET  /color/season-guide     — static educational guide for all seasons
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencies import ColorServiceDep, CurrentUser
from app.core.errors import NotFoundError
from app.schemas.base import APIResponse
from app.schemas.color import (
    ColorAnalysisRequest,
    ColorProfileOut,
    FullColorAnalysisResponse,
    SeasonClassification,
    PersonalPalette,
    ColorEntry,
)
from datetime import datetime, UTC

router = APIRouter(prefix="/color", tags=["Color Intelligence"])


# ── Helper: engine result → response schema ───────────────────────────────────

def _to_full_response(orm_profile, full_profile) -> FullColorAnalysisResponse:
    """Map engine FullColorProfile + ORM ColorProfile → API response."""
    s = full_profile.season

    def _ce(c) -> dict:
        return {"hex": c.hex, "name": c.name, "category": c.category,
                "season_fit": getattr(c, "season_fit", "best")}

    season = SeasonClassification(
        season=s.season,
        confidence=s.confidence,
        description=s.description,
        key_characteristics=s.key_characteristics,
        celebrity_examples=s.celebrity_examples,
        season_family=s.season_family,
        contrast_level=s.contrast_level,
        chroma_level=s.chroma_level,
        value_level=s.value_level,
    )

    palette = PersonalPalette(
        best=[ColorEntry(**_ce(c)) for c in full_profile.palette_best],
        neutrals=[ColorEntry(**_ce(c)) for c in full_profile.palette_neutrals],
        accents=[ColorEntry(**_ce(c)) for c in full_profile.palette_accents],
        avoid=[ColorEntry(**_ce(c)) for c in full_profile.palette_avoid],
        hero_color=ColorEntry(**_ce(full_profile.hero_color)),
    )

    return FullColorAnalysisResponse(
        profile_id=orm_profile.id,
        scan_id=orm_profile.scan_id,
        season=season,
        palette=palette,
        makeup=full_profile.makeup,
        lipstick=full_profile.lipstick,
        hair_color=full_profile.hair_color,
        outfits=full_profile.outfits,
        jewelry=full_profile.jewelry,
        computed_at=datetime.now(UTC).isoformat(),
        engine_version=orm_profile.engine_version,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/compute",
    response_model=APIResponse[FullColorAnalysisResponse],
    summary="Compute personal color profile",
    description=(
        "Derives the user's 12-season personal color profile from their facial "
        "scan data (skin tone, undertone, ITA°, Fitzpatrick phototype, hair color). "
        "Runs the Color Intelligence Engine inline (~5ms) and persists the result. "
        "Call after a successful facial scan is complete."
    ),
)
async def compute_color_profile(
    payload: ColorAnalysisRequest,
    current_user: CurrentUser,
    svc: ColorServiceDep,
) -> APIResponse[FullColorAnalysisResponse]:
    try:
        orm_profile, full_profile = await svc.compute_and_persist(
            user_id=current_user.id,
            scan_id=payload.scan_id,
            use_extended=payload.use_extended_seasons,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        )

    return APIResponse(
        data=_to_full_response(orm_profile, full_profile),
        message=f"Your color season is {full_profile.season.season.replace('_', ' ').title()}.",
    )


@router.get(
    "/profile",
    response_model=APIResponse[ColorProfileOut | None],
    summary="Get current active color profile",
    description="Returns the most recent computed color profile, or null if none exists.",
)
async def get_color_profile(
    current_user: CurrentUser,
    svc: ColorServiceDep,
) -> APIResponse[ColorProfileOut | None]:
    profile = await svc.get_active_profile(current_user.id)
    return APIResponse(
        data=ColorProfileOut.model_validate(profile) if profile else None
    )


@router.get(
    "/history",
    response_model=APIResponse[list[ColorProfileOut]],
    summary="List all color profile history",
)
async def get_color_history(
    current_user: CurrentUser,
    svc: ColorServiceDep,
) -> APIResponse[list[ColorProfileOut]]:
    profiles = await svc.get_profile_history(current_user.id)
    return APIResponse(data=[ColorProfileOut.model_validate(p) for p in profiles])


@router.delete(
    "/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a color profile",
)
async def delete_color_profile(
    profile_id: UUID,
    current_user: CurrentUser,
    svc: ColorServiceDep,
) -> None:
    try:
        await svc.delete_profile(current_user.id, profile_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        )


@router.get(
    "/season-guide",
    summary="Static educational guide for all 16 color seasons",
    description="Returns descriptions, key traits, and celebrity references for each season.",
)
async def season_guide() -> dict:
    """
    Static endpoint — no auth required. Returns rich educational data
    about all 16 color seasons (4 core + 12 extended).
    """
    from app.services.color_engine import _SEASON_META
    return {
        "seasons": [
            {
                "key": key,
                "family": meta["family"],
                "description": meta["desc"],
                "characteristics": meta["chars"],
                "celebrities": meta["celebs"],
                "contrast": meta["contrast"],
                "chroma": meta["chroma"],
                "value": meta["value"],
            }
            for key, meta in _SEASON_META.items()
        ]
    }

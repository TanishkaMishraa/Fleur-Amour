"""
AuraFit — Style DNA API endpoints (Stage 8).

Routes:
  GET  /style-dna/quiz              — quiz definition (questions, sections)
  POST /style-dna/quiz/start        — start or resume a quiz session
  POST /style-dna/quiz/{session_id}/respond  — save one question response
  POST /style-dna/quiz/{session_id}/complete — compute dimensions + archetypes
  GET  /style-dna/quiz/current      — current quiz session (if in progress)

  POST /style-dna/generate          — generate Style DNA Report from all user data
  GET  /style-dna/report            — get current active report
  GET  /style-dna/report/{id}       — get specific report by ID
  GET  /style-dna/report/history    — list all reports (newest first)
  GET  /style-dna/report/{id}/pdf   — download PDF or get URL

  GET  /style-dna/report/{id}/section/{section}  — one section for partial rendering
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import CurrentUser, StyleDNAServiceDep
from app.schemas.base import APIResponse

router = APIRouter(prefix="/style-dna", tags=["Style DNA"])


# ── Request schemas ────────────────────────────────────────────────────────────

class QuizResponseRequest(BaseModel):
    question_id:    str
    question_index: int
    answer_value:   str | None  = None
    answer_options: list[str] | None = None


# ── Quiz endpoints ─────────────────────────────────────────────────────────────

@router.get(
    "/quiz",
    summary="Get Style DNA quiz definition",
    description="Returns all 35 questions across 5 sections. Cached — no auth needed.",
)
async def get_quiz_definition(svc: StyleDNAServiceDep) -> dict:
    return svc.get_quiz_definition()


@router.post(
    "/quiz/start",
    summary="Start or resume a Style DNA quiz session",
)
async def start_quiz(
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict]:
    session_obj = await svc.start_quiz(current_user.id)
    return APIResponse(data={
        "session_id":   str(session_obj.id),
        "current_step": session_obj.current_step,
        "total_steps":  session_obj.total_steps,
        "status":       session_obj.status.value,
        "quiz_version": session_obj.quiz_version,
    })


@router.post(
    "/quiz/{session_id}/respond",
    summary="Save a question response",
)
async def quiz_respond(
    session_id: UUID,
    payload:    QuizResponseRequest,
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict]:
    result = await svc.save_response(
        session_id=session_id,
        question_id=payload.question_id,
        question_index=payload.question_index,
        answer_value=payload.answer_value,
        answer_options=payload.answer_options,
    )
    return APIResponse(data=result)


@router.post(
    "/quiz/{session_id}/complete",
    summary="Complete quiz and compute Style DNA dimensions",
)
async def complete_quiz(
    session_id: UUID,
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict]:
    quiz_session = await svc.complete_quiz(session_id)
    return APIResponse(data={
        "session_id":         str(quiz_session.id),
        "primary_archetype":  quiz_session.primary_archetype,
        "secondary_archetype":quiz_session.secondary_archetype,
        "budget_tier":        quiz_session.budget_tier,
        "lifestyle_tags":     quiz_session.lifestyle_tags,
        "style_axes": {
            "style":     quiz_session.style_axis,
            "energy":    quiz_session.energy_axis,
            "structure": quiz_session.structure_axis,
        },
        "occasion_mix": quiz_session.occasion_mix,
    })


# ── Report endpoints ───────────────────────────────────────────────────────────

@router.post(
    "/generate",
    summary="Generate Style DNA Report",
    description=(
        "Assembles all user data (facial scan, color profile, fragrance profile, "
        "quiz responses, wardrobe) and generates a complete Style DNA Report. "
        "Runs synchronously (~200ms) and dispatches PDF generation async. "
        "Requires at least a completed quiz session to generate meaningful content."
    ),
)
async def generate_report(
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict]:
    try:
        report = await svc.generate_report(current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return APIResponse(
        data={"report_id": str(report.id), "status": report.status.value},
        message="Your Style DNA Report is ready.",
    )


@router.get(
    "/report",
    summary="Get current active Style DNA Report",
)
async def get_current_report(
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict | None]:
    report = await svc.get_current_report(current_user.id)
    if not report:
        return APIResponse(data=None, message="No Style DNA Report found. Generate one first.")
    return APIResponse(data=_report_to_dict(report))


@router.get(
    "/report/history",
    summary="List all Style DNA Reports",
)
async def list_reports(
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[list]:
    reports = await svc.list_reports(current_user.id)
    return APIResponse(data=[
        {
            "id":         str(r.id),
            "status":     r.status.value,
            "headline":   r.headline,
            "pdf_url":    r.pdf_url,
            "is_current": r.is_current,
            "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
        }
        for r in reports
    ])


@router.get(
    "/report/{report_id}",
    summary="Get a specific Style DNA Report by ID",
)
async def get_report(
    report_id: UUID,
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict]:
    from sqlalchemy import select
    from app.models.style_dna import StyleDNAReport
    from sqlalchemy.ext.asyncio import AsyncSession

    # Access the session via svc._session
    result = await svc._session.execute(
        select(StyleDNAReport)
        .where(StyleDNAReport.id == report_id)
        .where(StyleDNAReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return APIResponse(data=_report_to_dict(report))


@router.get(
    "/report/{report_id}/section/{section_name}",
    summary="Get one report section for partial rendering",
)
async def get_report_section(
    report_id:    UUID,
    section_name: str,
    current_user: CurrentUser,
    svc: StyleDNAServiceDep,
) -> APIResponse[dict | None]:
    from sqlalchemy import select
    from app.models.style_dna import StyleDNAReport

    VALID_SECTIONS = {
        "beauty_profile", "skin_profile", "color_profile_section",
        "fashion_profile", "fragrance_profile_section", "hairstyle_profile",
        "recommendations", "personality", "occasion_guide",
    }
    if section_name not in VALID_SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid section '{section_name}'. Valid: {sorted(VALID_SECTIONS)}",
        )

    result = await svc._session.execute(
        select(StyleDNAReport)
        .where(StyleDNAReport.id == report_id)
        .where(StyleDNAReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return APIResponse(data=getattr(report, section_name, None))


def _report_to_dict(report) -> dict:
    return {
        "id":                        str(report.id),
        "status":                    report.status.value,
        "headline":                  report.headline,
        "narrative":                 report.narrative,
        "beauty_profile":            report.beauty_profile,
        "skin_profile":              report.skin_profile,
        "color_profile_section":     report.color_profile_section,
        "fashion_profile":           report.fashion_profile,
        "fragrance_profile_section": report.fragrance_profile_section,
        "hairstyle_profile":         report.hairstyle_profile,
        "recommendations":           report.recommendations,
        "personality":               report.personality,
        "occasion_guide":            report.occasion_guide,
        "pdf_url":                   report.pdf_url,
        "pdf_size_kb":               report.pdf_size_kb,
        "is_current":                report.is_current,
        "data_hash":                 report.data_hash,
        "created_at":                report.created_at.isoformat() if hasattr(report.created_at, "isoformat") else str(report.created_at),
    }

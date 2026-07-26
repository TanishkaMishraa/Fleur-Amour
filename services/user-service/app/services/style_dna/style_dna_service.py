"""
AuraFit — Style DNA Service (Stage 8).
Orchestrates the full pipeline:
  1. Assemble StyleDNAInput from all user data sources
  2. Run NLP report generator
  3. Dispatch PDF generation task (async)
  4. Persist StyleDNAReport to DB
  5. Return report content
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.analysis import FacialScan, FragranceProfile
from app.models.color import ColorProfile
from app.models.profile import UserProfile
from app.models.style_dna import QuizResponse, QuizSession, QuizStatus, StyleDNAReport, StyleDNAStatus
from app.models.user import User
from app.services.style_dna.quiz_engine import (
    QUIZ_QUESTIONS, QUIZ_VERSION,
    classify_archetypes, compute_dimensions,
)
from app.services.style_dna.report_generator import StyleDNAInput, StyleDNANLPEngine

logger = get_logger(__name__)
_nlp = StyleDNANLPEngine()


class StyleDNAService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Quiz management ────────────────────────────────────────────────────────

    def get_quiz_definition(self) -> dict:
        """Return the full quiz structure for the frontend."""
        sections: dict[str, list] = {}
        for q in QUIZ_QUESTIONS:
            if q.section not in sections:
                sections[q.section] = []
            sections[q.section].append({
                "id":           q.id,
                "index":        q.index,
                "type":         q.type,
                "question":     q.question,
                "subtitle":     q.subtitle,
                "options":      [
                    {"id": o.id, "label": o.label, "image": o.image}
                    for o in q.options
                ],
                "scale_min":    q.scale_min,
                "scale_max":    q.scale_max,
                "scale_labels": list(q.scale_labels),
                "max_select":   q.max_select,
            })
        return {
            "version":     QUIZ_VERSION,
            "total":       len(QUIZ_QUESTIONS),
            "sections":    sections,
            "section_order":["personality", "fashion", "lifestyle", "budget", "beauty"],
        }

    async def start_quiz(self, user_id: uuid.UUID) -> QuizSession:
        """Create (or resume) an in-progress quiz session."""
        # Check for existing in-progress session
        result = await self._session.execute(
            select(QuizSession)
            .where(QuizSession.user_id == user_id)
            .where(QuizSession.status == QuizStatus.IN_PROGRESS)
            .order_by(QuizSession.created_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        session_obj = QuizSession(
            user_id=user_id,
            quiz_version=QUIZ_VERSION,
            status=QuizStatus.IN_PROGRESS,
            current_step=0,
            total_steps=len(QUIZ_QUESTIONS),
        )
        self._session.add(session_obj)
        await self._session.flush()
        return session_obj

    async def save_response(
        self,
        session_id: uuid.UUID,
        question_id: str,
        question_index: int,
        answer_value: str | None,
        answer_options: list | None,
    ) -> dict:
        """
        Save one quiz response. Pre-compute answer_scores from quiz definition.
        Returns {current_step, total_steps, is_complete}.
        """
        # Find the question definition
        q_def = next((q for q in QUIZ_QUESTIONS if q.id == question_id), None)
        answer_scores = {}

        if q_def:
            if q_def.type in ("single",) and answer_value:
                opt = next((o for o in q_def.options if o.id == answer_value), None)
                if opt:
                    answer_scores = opt.scores
            elif q_def.type in ("multi",) and answer_options:
                # Merge scores from all selected options (mean)
                all_scores: dict[str, list[float]] = {}
                for opt_id in answer_options:
                    opt = next((o for o in q_def.options if o.id == opt_id), None)
                    if opt:
                        for k, v in opt.scores.items():
                            all_scores.setdefault(k, []).append(v)
                answer_scores = {k: sum(vs)/len(vs) for k, vs in all_scores.items()}
            elif q_def.type == "scale" and answer_value:
                answer_scores = {"scale_value": float(answer_value) / q_def.scale_max}

        # Upsert response
        existing_resp = (await self._session.execute(
            select(QuizResponse)
            .where(QuizResponse.session_id == session_id)
            .where(QuizResponse.question_id == question_id)
        )).scalar_one_or_none()

        if existing_resp:
            existing_resp.answer_value   = answer_value
            existing_resp.answer_options = answer_options
            existing_resp.answer_scores  = answer_scores
            self._session.add(existing_resp)
        else:
            self._session.add(QuizResponse(
                session_id=session_id,
                question_id=question_id,
                question_index=question_index,
                answer_value=answer_value,
                answer_options=answer_options,
                answer_scores=answer_scores,
            ))

        # Update quiz session progress
        quiz_session = await self._session.get(QuizSession, session_id)
        if quiz_session:
            quiz_session.current_step = max(quiz_session.current_step, question_index + 1)
            self._session.add(quiz_session)

        await self._session.flush()

        return {
            "current_step":  quiz_session.current_step if quiz_session else question_index + 1,
            "total_steps":   len(QUIZ_QUESTIONS),
            "is_complete":   (quiz_session.current_step >= len(QUIZ_QUESTIONS)) if quiz_session else False,
        }

    async def complete_quiz(self, session_id: uuid.UUID) -> QuizSession:
        """
        Compute personality dimensions, classify archetypes, mark session complete.
        """
        quiz_session = await self._session.get(QuizSession, session_id)
        if not quiz_session:
            raise ValueError(f"QuizSession {session_id} not found")

        responses = (await self._session.execute(
            select(QuizResponse)
            .where(QuizResponse.session_id == session_id)
            .order_by(QuizResponse.question_index)
        )).scalars().all()

        resp_dicts = [
            {
                "question_id":   r.question_id,
                "answer_value":  r.answer_value,
                "answer_options":r.answer_options,
                "answer_scores": r.answer_scores,
            }
            for r in responses
        ]

        computed = compute_dimensions(resp_dicts)
        dims     = computed["dimensions"]
        primary, secondary = classify_archetypes(dims)

        quiz_session.status               = QuizStatus.COMPLETED
        quiz_session.style_axis           = dims.get("style_axis")
        quiz_session.energy_axis          = dims.get("energy_axis")
        quiz_session.structure_axis       = dims.get("structure_axis")
        quiz_session.occasion_mix         = {
            "work":    dims.get("occasion_work", 0.33),
            "casual":  dims.get("occasion_casual", 0.33),
            "evening": dims.get("occasion_evening", 0.33),
        }
        quiz_session.lifestyle_tags       = computed.get("lifestyle_tags", [])
        quiz_session.budget_tier          = computed.get("budget_tier", "mid")
        quiz_session.primary_archetype    = primary
        quiz_session.secondary_archetype  = secondary
        quiz_session.completed_at         = datetime.now(UTC).isoformat()
        self._session.add(quiz_session)
        await self._session.flush()

        logger.info(
            "style_dna.quiz_complete",
            user_id=str(quiz_session.user_id),
            primary=primary,
            secondary=secondary,
        )
        return quiz_session

    # ── Report generation ─────────────────────────────────────────────────────

    async def generate_report(self, user_id: uuid.UUID) -> StyleDNAReport:
        """
        Full pipeline:
          1. Assemble all user data
          2. Generate report content via NLP engine
          3. Persist StyleDNAReport
          4. Dispatch PDF Celery task
        """
        # 1. Assemble input
        inp = await self._assemble_input(user_id)
        if inp is None:
            raise ValueError("Insufficient data to generate Style DNA Report. Please complete a facial scan and the style quiz first.")

        # 2. Deactivate previous reports
        await self._session.execute(
            StyleDNAReport.__table__.update()
            .where(StyleDNAReport.user_id == user_id)
            .values(is_current=False)
        )

        # 3. Create report record (QUEUED)
        report = StyleDNAReport(
            user_id=user_id,
            status=StyleDNAStatus.GENERATING,
            report_version="1.0",
            is_current=True,
        )
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report)

        try:
            # 4. Generate content
            content = _nlp.generate(inp)

            report.headline                  = content.headline
            report.narrative                 = content.narrative
            report.beauty_profile            = content.beauty_profile
            report.skin_profile              = content.skin_profile
            report.color_profile_section     = content.color_profile_section
            report.fashion_profile           = content.fashion_profile
            report.fragrance_profile_section = content.fragrance_profile_section
            report.hairstyle_profile         = content.hairstyle_profile
            report.recommendations           = content.recommendations
            report.personality               = content.personality
            report.occasion_guide            = content.occasion_guide
            report.data_hash                 = content.data_hash
            report.status                    = StyleDNAStatus.READY

        except Exception as exc:
            report.status = StyleDNAStatus.FAILED
            logger.exception("style_dna.generation_failed", user_id=str(user_id), error=str(exc))
            self._session.add(report)
            await self._session.flush()
            raise

        self._session.add(report)
        await self._session.flush()

        # 5. Dispatch async PDF task
        try:
            from app.tasks.style_dna_tasks import generate_pdf
            task = generate_pdf.apply_async(
                kwargs={"report_id": str(report.id)},
                countdown=5,
            )
            report.celery_task_id = task.id
            self._session.add(report)
            await self._session.flush()
        except Exception as exc:
            logger.warning("style_dna.pdf_task_dispatch_failed", error=str(exc))

        logger.info("style_dna.report_ready", user_id=str(user_id), report_id=str(report.id))
        return report

    async def get_current_report(self, user_id: uuid.UUID) -> StyleDNAReport | None:
        result = await self._session.execute(
            select(StyleDNAReport)
            .where(StyleDNAReport.user_id == user_id)
            .where(StyleDNAReport.is_current == True)   # noqa: E712
            .where(StyleDNAReport.status == StyleDNAStatus.READY)
            .order_by(StyleDNAReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_reports(self, user_id: uuid.UUID) -> list[StyleDNAReport]:
        result = await self._session.execute(
            select(StyleDNAReport)
            .where(StyleDNAReport.user_id == user_id)
            .order_by(StyleDNAReport.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Data assembly ─────────────────────────────────────────────────────────

    async def _assemble_input(self, user_id: uuid.UUID) -> StyleDNAInput | None:
        """Gather all available user data and assemble StyleDNAInput."""

        # User + profile
        user = await self._session.get(User, user_id)
        if not user:
            return None

        profile_result = await self._session.execute(
            select(UserProfile)
            .where(UserProfile.user_id == user_id)
            .options(selectinload(UserProfile.fragrance_profile))
        )
        profile: UserProfile | None = profile_result.scalar_one_or_none()

        # Latest active facial scan
        scan_result = await self._session.execute(
            select(FacialScan)
            .where(FacialScan.user_id == user_id)
            .where(FacialScan.is_active == True)   # noqa: E712
            .order_by(FacialScan.created_at.desc())
            .limit(1)
        )
        scan: FacialScan | None = scan_result.scalar_one_or_none()

        # Active color profile
        color_result = await self._session.execute(
            select(ColorProfile)
            .where(ColorProfile.user_id == user_id)
            .where(ColorProfile.is_active == True)   # noqa: E712
            .order_by(ColorProfile.created_at.desc())
            .limit(1)
        )
        color: ColorProfile | None = color_result.scalar_one_or_none()

        # Latest completed quiz
        quiz_result = await self._session.execute(
            select(QuizSession)
            .where(QuizSession.user_id == user_id)
            .where(QuizSession.status == QuizStatus.COMPLETED)
            .order_by(QuizSession.created_at.desc())
            .limit(1)
        )
        quiz: QuizSession | None = quiz_result.scalar_one_or_none()

        # Extract data with safe fallbacks
        p = profile
        s = scan
        c = color
        q = quiz

        skin_analysis  = s.skin_analysis  or {} if s else {}
        facial_features= s.facial_features or {} if s else {}
        sa_skin        = skin_analysis.get("skin_tone", {}) if isinstance(skin_analysis.get("skin_tone"), dict) else {}
        ha             = skin_analysis.get("hair_analysis", {}) or {}
        acne_data      = skin_analysis.get("acne_analysis", {}) or {}
        symmetry       = skin_analysis.get("symmetry", {})

        return StyleDNAInput(
            user_id=user_id,
            full_name=user.full_name or "Friend",
            age_range=p.age_range if p else None,
            # Physical
            skin_tone=sa_skin.get("tone") or (p.skin_tone if p else None),
            skin_type=p.skin_type if p else None,
            undertone=sa_skin.get("undertone") or (p.undertone if p else None),
            skin_concerns=list(p.skin_concerns or []) if p else [],
            face_shape=s.face_shape if s else None,
            body_shape=p.body_shape if p else None,
            hair_type=ha.get("hair_type") or (p.hair_type if p else None),
            hair_color=ha.get("dominant_color") or (p.hair_color if p else None),
            eye_color=p.eye_color if p else None,
            height_cm=p.height_cm if p else None,
            # AI-derived
            skin_analysis=skin_analysis,
            facial_features=facial_features,
            acne_data=acne_data,
            hair_analysis=ha,
            symmetry_score=symmetry.get("overall_score") if isinstance(symmetry, dict) else None,
            # Color
            color_season=c.season if c else None,
            color_season_family=self._season_family(c.season if c else None),
            palette_best=c.palette_best or [] if c else [],
            palette_neutrals=c.palette_neutrals or [] if c else [],
            palette_accents=c.palette_accents or [] if c else [],
            makeup_recs=c.makeup_recommendations or {} if c else {},
            # Fragrance
            fragrance_family=list(p.fragrance_family or []) if p else [],
            preferred_notes=list(p.fragrance_profile.preferred_notes or []) if (p and p.fragrance_profile) else [],
            avoided_notes=list(p.fragrance_profile.avoided_notes or []) if (p and p.fragrance_profile) else [],
            intensity_pref=p.fragrance_profile.intensity_preference if (p and p.fragrance_profile) else None,
            longevity_pref=p.fragrance_profile.longevity_preference if (p and p.fragrance_profile) else None,
            # Quiz
            primary_archetype=q.primary_archetype if q else None,
            secondary_archetype=q.secondary_archetype if q else None,
            style_dimensions={
                "style_axis":       q.style_axis or 0.5,
                "energy_axis":      q.energy_axis or 0.5,
                "structure_axis":   q.structure_axis or 0.5,
                "romance_axis":     0.5,
                "practicality":     0.5,
                "experimentalism":  0.5,
            } if q else {},
            budget_tier=q.budget_tier if q else (p.budget_range if p else "mid"),
            lifestyle_tags=list(q.lifestyle_tags or []) if q else [],
            occasion_mix=q.occasion_mix or {} if q else {},
            top_categories=[],
            wardrobe_count=0,
            currency=p.currency if p else "INR",
            extra={"avoided_ingredients": list(p.avoided_ingredients or []) if p else []},
        )

    @staticmethod
    def _season_family(season: str | None) -> str | None:
        if not season:
            return None
        for family in ("spring", "summer", "autumn", "winter"):
            if family in season.lower():
                return family
        return None

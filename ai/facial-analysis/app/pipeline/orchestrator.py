"""
AuraFit — Facial Analysis Pipeline Orchestrator.
Coordinates: preprocessing → detection → parallel analyzers → postprocessing.

Design:
  - Detection runs first (blocking — all analyzers depend on landmarks).
  - Independent analyzers (skin tone, age, hair, acne, dark circles, texture,
    symmetry, face shape) run concurrently in a thread pool — they are CPU-bound
    OpenCV/NumPy operations with no shared mutable state.
  - DeepFace (age) is GPU-capable and the slowest step; it runs in its own
    thread so CPU-bound analyzers aren't blocked waiting on it.
  - Postprocessing (recommendations) runs last, after all results are ready.

This orchestration keeps total wall-clock time close to the slowest single
analyzer (~typically DeepFace age estimation, 200-600ms) rather than the sum
of all analyzers (which would be 1-2s sequential).
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.core.config import get_settings
from app.pipeline.analyzers.acne_analyzer import AcneAnalyzer
from app.pipeline.analyzers.age_analyzer import AgeAnalyzer
from app.pipeline.analyzers.dark_circle_analyzer import DarkCircleAnalyzer
from app.pipeline.analyzers.face_shape_analyzer import FaceShapeAnalyzer
from app.pipeline.analyzers.hair_analyzer import HairAnalyzer
from app.pipeline.analyzers.skin_texture_analyzer import SkinTextureAnalyzer
from app.pipeline.analyzers.skin_tone_analyzer import SkinToneAnalyzer
from app.pipeline.analyzers.symmetry_analyzer import SymmetryAnalyzer
from app.pipeline.detectors.face_detector import FaceDetector
from app.pipeline.postprocessors.recommendation_generator import RecommendationGenerator
from app.pipeline.processors.image_processor import ImageProcessor, ProcessedImage
from app.schemas.analysis_schemas import (
    AnalysisErrorResponse,
    AnalysisResult,
    QualityCheck,
    SyncAnalyzeResponse,
)

_settings = get_settings()

PIPELINE_VERSION = "1.0.0"

# Shared thread pool for CPU-bound analyzer steps.
# Sized to leave headroom for the DeepFace executor (4 workers) +
# the FastAPI event loop on a typical 4-vCPU worker instance.
_analyzer_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="analyzer")


class AnalysisPipeline:
    """
    Singleton-friendly orchestrator. Construct once at app startup;
    re-use across requests (model loading is the expensive part).
    """

    def __init__(self) -> None:
        self._image_processor = ImageProcessor()
        self._face_detector    = FaceDetector(_settings)
        self._skin_tone        = SkinToneAnalyzer()
        self._face_shape       = FaceShapeAnalyzer()
        self._age              = AgeAnalyzer(_settings)
        self._hair             = HairAnalyzer()
        self._acne             = AcneAnalyzer()
        self._dark_circles     = DarkCircleAnalyzer()
        self._texture          = SkinTextureAnalyzer()
        self._symmetry         = SymmetryAnalyzer()
        self._recommender      = RecommendationGenerator()

    # ── Public API ───────────────────────────────────────────────────────────

    def run_from_s3(self, s3_key: str, task_id: str) -> SyncAnalyzeResponse:
        """Full pipeline: download from S3 → analyze → return result."""
        start = time.perf_counter()
        try:
            image = self._image_processor.load_from_s3(s3_key)
        except Exception as exc:
            return self._error_response(
                task_id, "IMAGE_LOAD_FAILED",
                f"Could not load or decode image: {exc}", retryable=True,
            )
        return self._run(image, task_id, start)

    def run_from_bytes(self, data: bytes, task_id: str) -> SyncAnalyzeResponse:
        """Used for synchronous /analyze calls with direct upload, and tests."""
        start = time.perf_counter()
        try:
            image = self._image_processor.load_from_bytes(data)
        except Exception as exc:
            return self._error_response(
                task_id, "IMAGE_LOAD_FAILED",
                f"Could not load or decode image: {exc}", retryable=True,
            )
        return self._run(image, task_id, start)

    # ── Core pipeline ────────────────────────────────────────────────────────

    def _run(self, image: ProcessedImage, task_id: str, start: float) -> SyncAnalyzeResponse:
        # ── Stage 1: Face detection + mesh (blocking — everything depends on it) ──
        detection = self._face_detector.detect(image.rgb)

        if not detection.detected:
            return self._error_response(
                task_id, "NO_FACE_DETECTED",
                "No face was detected in the image. Please use a clear, "
                "front-facing photo with good lighting.",
                retryable=False,
            )

        quality = self._build_quality(image.quality, detection)
        if not quality.passed:
            return self._error_response(
                task_id, "QUALITY_CHECK_FAILED",
                quality.rejection_reason or "Image quality too low for analysis.",
                retryable=False,
                quality=quality,
            )

        bbox = detection.bounding_box
        face_bbox_tuple = (bbox.x, bbox.y, bbox.w, bbox.h)
        landmarks   = detection.landmarks
        mesh_points = detection.mesh_points

        # ── Stage 2: Run all independent analyzers concurrently ───────────────
        futures: dict[str, Any] = {}
        futures["face_shape"]   = _analyzer_pool.submit(self._face_shape.analyze, landmarks)
        futures["skin_tone"]    = _analyzer_pool.submit(self._skin_tone.analyze, image.bgr, landmarks, mesh_points)
        futures["age"]          = _analyzer_pool.submit(self._age.analyze, image.rgb)
        futures["hair"]         = _analyzer_pool.submit(self._hair.analyze, image.bgr, face_bbox_tuple)
        futures["acne"]         = _analyzer_pool.submit(self._acne.analyze, image.bgr, face_bbox_tuple)
        futures["dark_circles"] = _analyzer_pool.submit(self._dark_circles.analyze, image.bgr, mesh_points)
        futures["texture"]      = _analyzer_pool.submit(self._texture.analyze, image.bgr, face_bbox_tuple)
        futures["symmetry"]     = _analyzer_pool.submit(self._symmetry.analyze, landmarks)

        results: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for name, future in futures.items():
            try:
                results[name] = future.result(timeout=_settings.INFERENCE_TIMEOUT)
            except Exception as exc:
                errors[name] = str(exc)

        # If any critical analyzer failed entirely, fail the request.
        # Non-critical analyzers (hair, acne, dark_circles, texture, symmetry,
        # age) degrade gracefully via their own fallback paths, so we only
        # hard-fail on the two geometry-critical ones.
        for critical in ("face_shape", "skin_tone"):
            if critical not in results:
                return self._error_response(
                    task_id, "ANALYZER_FAILED",
                    f"Critical analyzer '{critical}' failed: {errors.get(critical)}",
                    retryable=True,
                )

        # ── Stage 3: Aggregate skin concerns from sub-analyzers ────────────────
        skin_concerns = list(results["acne"].concerns) if "acne" in results else []

        # ── Stage 4: Build the result object (without recommendations yet) ─────
        elapsed_ms = (time.perf_counter() - start) * 1000

        result = AnalysisResult(
            pipeline_version=PIPELINE_VERSION,
            processing_time_ms=round(elapsed_ms, 2),
            quality=quality,
            face_shape=results["face_shape"],
            landmarks=landmarks,
            mesh_points=mesh_points,
            bounding_box=bbox,
            symmetry=results.get("symmetry") or self._symmetry.analyze(landmarks),
            skin_tone=results["skin_tone"],
            age_estimation=results.get("age") or self._age._fallback(),
            acne_analysis=results.get("acne") or self._acne._empty_result(),
            dark_circles=results.get("dark_circles") or self._dark_circles.analyze(image.bgr, mesh_points),
            skin_texture=results.get("texture") or self._texture._empty(),
            skin_concerns=skin_concerns,
            hair_analysis=results.get("hair") or self._hair._empty_result(),
            makeup_recommendations={},
            skincare_recommendations={},
            hairstyle_recommendations=[],
        )

        # ── Stage 5: Postprocessing — generate recommendations ─────────────────
        makeup, skincare, hairstyles = self._recommender.generate(result)
        result.makeup_recommendations   = makeup
        result.skincare_recommendations = skincare
        result.hairstyle_recommendations = hairstyles

        # Final timing includes recommendation generation
        result.processing_time_ms = round((time.perf_counter() - start) * 1000, 2)

        return SyncAnalyzeResponse(success=True, task_id=task_id, result=result, error=None)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_quality(self, base: QualityCheck, detection: Any) -> QualityCheck:
        """Merge image-level quality with face-detection-level quality flags."""
        face_centered = detection.quality_flags.get("face_centered", True)
        no_occlusion  = detection.quality_flags.get("no_occlusion", True)

        passed = base.passed and face_centered and no_occlusion
        reason = base.rejection_reason
        if not face_centered:
            reason = "Face is not well-centered in the frame. Please center your face and retake the photo."
        elif not no_occlusion:
            reason = "Part of your face appears obscured. Remove glasses, masks, or hair covering your face."

        return QualityCheck(
            passed=passed,
            brisque_score=base.brisque_score,
            face_visible=True,
            face_centered=face_centered,
            good_lighting=base.good_lighting,
            no_occlusion=no_occlusion,
            rejection_reason=None if passed else reason,
        )

    def _error_response(
        self,
        task_id: str,
        code: str,
        message: str,
        *,
        retryable: bool,
        quality: QualityCheck | None = None,
    ) -> SyncAnalyzeResponse:
        return SyncAnalyzeResponse(
            success=False,
            task_id=task_id,
            result=None,
            error=AnalysisErrorResponse(
                task_id=task_id,
                error_code=code,
                error_message=message,
                retryable=retryable,
            ),
        )

    def close(self) -> None:
        """Release MediaPipe resources. Call on app shutdown."""
        self._face_detector.close()


# ── Module-level singleton ──────────────────────────────────────────────────
# Constructed once at app startup (see app/main.py lifespan).
_pipeline: AnalysisPipeline | None = None


def get_pipeline() -> AnalysisPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = AnalysisPipeline()
    return _pipeline


def shutdown_pipeline() -> None:
    global _pipeline
    if _pipeline is not None:
        _pipeline.close()
        _pipeline = None

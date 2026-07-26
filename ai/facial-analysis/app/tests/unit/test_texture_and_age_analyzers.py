"""
Unit tests — SkinTextureAnalyzer and AgeAnalyzer.
SkinTextureAnalyzer: verifies Haralick features, roughness, and overall score
bounds; also checks that a noisy image scores lower than a smooth one.
AgeAnalyzer: tests the fallback path (no DeepFace in CI) returns a valid result.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.pipeline.analyzers.skin_texture_analyzer import SkinTextureAnalyzer
from app.pipeline.analyzers.age_analyzer import AgeAnalyzer
from app.schemas.analysis_schemas import AgeEstimationResult, SkinTextureResult
from unittest.mock import MagicMock


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def smooth_skin_image() -> np.ndarray:
    """Flat, uniform-colour image — very low Laplacian variance (smooth)."""
    return np.full((300, 300, 3), (165, 150, 168), dtype=np.uint8)


@pytest.fixture
def rough_skin_image() -> np.ndarray:
    """
    High-frequency noise image simulating rough/textured skin.
    Random per-pixel variation gives a high Laplacian variance.
    """
    rng = np.random.default_rng(seed=42)
    return rng.integers(80, 200, size=(300, 300, 3), dtype=np.uint8)


_FULL_BBOX = (0, 0, 300, 300)
_HALF_BBOX = (0, 0, 150, 150)


class TestSkinTextureAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = SkinTextureAnalyzer()

    def test_smooth_face_scores_high(self, smooth_skin_image: np.ndarray) -> None:
        result = self.analyzer.analyze(smooth_skin_image, _FULL_BBOX)
        assert isinstance(result, SkinTextureResult)
        assert result.overall_score > 0.4  # smooth should score at least middling

    def test_rough_face_scores_lower_than_smooth(
        self, smooth_skin_image: np.ndarray, rough_skin_image: np.ndarray
    ) -> None:
        smooth_result = self.analyzer.analyze(smooth_skin_image, _FULL_BBOX)
        rough_result  = self.analyzer.analyze(rough_skin_image,  _FULL_BBOX)
        assert smooth_result.overall_score >= rough_result.overall_score

    def test_all_scores_within_bounds(
        self, smooth_skin_image: np.ndarray, rough_skin_image: np.ndarray
    ) -> None:
        for img in (smooth_skin_image, rough_skin_image):
            result = self.analyzer.analyze(img, _FULL_BBOX)
            assert 0.0 <= result.overall_score    <= 1.0
            assert 0.0 <= result.roughness        <= 1.0
            assert 0.0 <= result.pore_visibility  <= 1.0
            assert 0.0 <= result.evenness         <= 1.0

    def test_haralick_features_present(self, smooth_skin_image: np.ndarray) -> None:
        result = self.analyzer.analyze(smooth_skin_image, _FULL_BBOX)
        for key in ("contrast", "homogeneity", "energy", "correlation"):
            assert key in result.haralick_features
            assert isinstance(result.haralick_features[key], float)

    def test_empty_bbox_returns_defaults(self, smooth_skin_image: np.ndarray) -> None:
        result = self.analyzer.analyze(smooth_skin_image, (0, 0, 0, 0))
        # Should return _empty() defaults without raising
        assert isinstance(result, SkinTextureResult)
        assert result.overall_score == 0.5  # _empty() default

    def test_sub_region_bbox(self, rough_skin_image: np.ndarray) -> None:
        """Using a sub-image bbox should still return a valid result."""
        result = self.analyzer.analyze(rough_skin_image, _HALF_BBOX)
        assert isinstance(result, SkinTextureResult)
        assert 0.0 <= result.overall_score <= 1.0

    def test_lbp_score_is_float_or_none(self, smooth_skin_image: np.ndarray) -> None:
        result = self.analyzer.analyze(smooth_skin_image, _FULL_BBOX)
        assert result.lbp_score is None or isinstance(result.lbp_score, float)


# ── AgeAnalyzer ─────────────────────────────────────────────────────────────

class TestAgeAnalyzer:
    """
    AgeAnalyzer wraps DeepFace which is not available in the unit-test
    environment (no face images, no GPU). Tests focus on the fallback
    path and the _fallback() helper directly.
    """

    def setup_method(self) -> None:
        settings = MagicMock()
        settings.DEEPFACE_BACKEND = "opencv"
        settings.DEEPFACE_ENFORCE_DETECTION = False
        settings.INFERENCE_TIMEOUT = 5
        self.analyzer = AgeAnalyzer(settings)

    def test_fallback_returns_valid_result(self) -> None:
        result = self.analyzer._fallback()
        assert isinstance(result, AgeEstimationResult)
        assert 1 <= result.estimated_age <= 100
        assert "-" in result.age_range or "+" in result.age_range or result.age_range.startswith("Under")
        assert result.confidence == 0.0
        assert result.model == "fallback"

    def test_analyze_with_empty_array_uses_fallback(self) -> None:
        """Empty/invalid image causes DeepFace to throw; should return fallback."""
        dummy_rgb = np.zeros((64, 64, 3), dtype=np.uint8)
        result = self.analyzer.analyze(dummy_rgb)
        assert isinstance(result, AgeEstimationResult)
        assert 1 <= result.estimated_age <= 100

    def test_age_range_labels(self) -> None:
        """All standard age ranges have the right format."""
        for age, expected_range in [
            (10, "Under 18"), (20, "18-24"), (30, "25-34"),
            (40, "35-44"), (50, "45-54"), (60, "55-64"), (70, "65+"),
        ]:
            from app.pipeline.analyzers.age_analyzer import _age_range
            assert _age_range(age) == expected_range

    def test_result_age_clamped(self) -> None:
        """Estimated age should always be in [1, 100]."""
        result = self.analyzer._fallback()
        assert 1 <= result.estimated_age <= 100

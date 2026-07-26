"""
Unit tests — SymmetryAnalyzer.
Verifies overall/per-feature symmetry scoring is bounded [0,1] and that a
perfectly mirrored landmark set scores near 1.0 while a deliberately
asymmetric set scores lower.
"""
from __future__ import annotations

import copy

from app.pipeline.analyzers.symmetry_analyzer import SymmetryAnalyzer
from app.schemas.analysis_schemas import FaceLandmarks


class TestSymmetryAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = SymmetryAnalyzer()

    def test_symmetric_face_scores_high(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        result = self.analyzer.analyze(synthetic_face_landmarks)
        assert result.overall_score > 0.85
        assert result.eye_symmetry > 0.8
        assert result.mouth_symmetry > 0.8
        assert "symmetr" in result.deviation_summary.lower() or "harmonious" in result.deviation_summary.lower()

    def test_asymmetric_face_scores_lower(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        asym = copy.deepcopy(synthetic_face_landmarks)
        # Push the right eye down and outward — breaks both y-level and
        # midline-distance symmetry simultaneously.
        asym.right_eye = [0.78, 0.50]
        result = self.analyzer.analyze(asym)
        baseline = self.analyzer.analyze(synthetic_face_landmarks)
        assert result.overall_score < baseline.overall_score
        assert result.eye_symmetry < baseline.eye_symmetry

    def test_all_scores_within_bounds(self, synthetic_face_landmarks: FaceLandmarks, round_face_landmarks: FaceLandmarks) -> None:
        for lm in (synthetic_face_landmarks, round_face_landmarks):
            result = self.analyzer.analyze(lm)
            for field in ("overall_score", "eye_symmetry", "mouth_symmetry", "nostril_symmetry", "jaw_symmetry"):
                value = getattr(result, field)
                assert 0.0 <= value <= 1.0, f"{field}={value} out of bounds"

    def test_overall_is_weighted_combination(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        result = self.analyzer.analyze(synthetic_face_landmarks)
        expected = round(
            result.eye_symmetry * 0.35
            + result.mouth_symmetry * 0.25
            + result.nostril_symmetry * 0.20
            + result.jaw_symmetry * 0.20,
            3,
        )
        assert abs(result.overall_score - expected) < 1e-6

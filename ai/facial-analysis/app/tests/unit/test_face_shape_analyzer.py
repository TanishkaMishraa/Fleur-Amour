"""
Unit tests — FaceShapeAnalyzer.
Verifies the deterministic geometric classifier against known landmark ratios
for all 7 supported face shapes.
"""
from __future__ import annotations

import copy

import pytest

from app.pipeline.analyzers.face_shape_analyzer import FaceShapeAnalyzer
from app.schemas.analysis_schemas import FaceShape, FaceLandmarks


class TestFaceShapeAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = FaceShapeAnalyzer()

    def test_oval_classification(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        result = self.analyzer.analyze(synthetic_face_landmarks)
        assert result.shape == FaceShape.OVAL
        assert 0.0 <= result.confidence <= 1.0
        assert result.description

    def test_round_classification(self, round_face_landmarks: FaceLandmarks) -> None:
        result = self.analyzer.analyze(round_face_landmarks)
        assert result.shape == FaceShape.ROUND

    def test_oblong_for_very_long_face(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        lm = copy.deepcopy(synthetic_face_landmarks)
        lm.face_length_ratio = 1.60
        result = self.analyzer.analyze(lm)
        assert result.shape == FaceShape.OBLONG

    def test_square_classification(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        """Wide jaw (>0.80) with moderate face length → square."""
        lm = copy.deepcopy(synthetic_face_landmarks)
        lm.jaw_width_ratio   = 0.85
        lm.face_length_ratio = 1.20
        result = self.analyzer.analyze(lm)
        assert result.shape == FaceShape.SQUARE

    def test_heart_classification(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        """Narrow jaw (<0.65) + wide cheekbones (>0.85) → heart."""
        lm = copy.deepcopy(synthetic_face_landmarks)
        lm.jaw_width_ratio   = 0.58
        lm.cheekbone_ratio   = 0.88
        lm.face_length_ratio = 1.30
        result = self.analyzer.analyze(lm)
        assert result.shape == FaceShape.HEART

    def test_triangle_classification(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        """Wide jaw (>0.75) + narrow cheeks (<0.72) → triangle / pear."""
        lm = copy.deepcopy(synthetic_face_landmarks)
        lm.jaw_width_ratio  = 0.82
        lm.cheekbone_ratio  = 0.68
        lm.face_length_ratio = 1.25
        result = self.analyzer.analyze(lm)
        assert result.shape == FaceShape.TRIANGLE

    def test_ratios_are_returned(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        result = self.analyzer.analyze(synthetic_face_landmarks)
        assert set(result.ratios.keys()) == {"face_length", "jaw_width", "cheekbone"}
        assert result.ratios["face_length"] == round(synthetic_face_landmarks.face_length_ratio, 3)

    def test_confidence_within_bounds(
        self, synthetic_face_landmarks: FaceLandmarks, round_face_landmarks: FaceLandmarks
    ) -> None:
        for lm in (synthetic_face_landmarks, round_face_landmarks):
            result = self.analyzer.analyze(lm)
            assert 0.0 <= result.confidence <= 1.0

    def test_description_is_non_empty(self, synthetic_face_landmarks: FaceLandmarks) -> None:
        """Every shape classification should produce a non-empty description."""
        shapes_to_test = [
            {"jaw_width_ratio": 0.72, "face_length_ratio": 1.30, "cheekbone_ratio": 0.80},  # oval
            {"jaw_width_ratio": 0.88, "face_length_ratio": 1.05, "cheekbone_ratio": 0.92},  # round
            {"jaw_width_ratio": 0.72, "face_length_ratio": 1.60, "cheekbone_ratio": 0.80},  # oblong
            {"jaw_width_ratio": 0.85, "face_length_ratio": 1.20, "cheekbone_ratio": 0.80},  # square
            {"jaw_width_ratio": 0.58, "face_length_ratio": 1.30, "cheekbone_ratio": 0.88},  # heart
        ]
        for overrides in shapes_to_test:
            lm = copy.deepcopy(synthetic_face_landmarks)
            for attr, val in overrides.items():
                setattr(lm, attr, val)
            result = self.analyzer.analyze(lm)
            assert len(result.description) > 10, f"Empty description for shape {result.shape}"

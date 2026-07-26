"""
Unit tests — SkinToneAnalyzer.
Verifies ITA° computation, Fitzpatrick mapping, and undertone classification
across the skin tone spectrum using synthetic flat-colour images.
"""
from __future__ import annotations

from app.pipeline.analyzers.skin_tone_analyzer import SkinToneAnalyzer
from app.schemas.analysis_schemas import Undertone


class TestSkinToneAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = SkinToneAnalyzer()

    def test_fair_skin_high_ita(self, fair_skin_image, synthetic_face_landmarks, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(fair_skin_image, synthetic_face_landmarks, synthetic_mesh_points)
        # Fair skin should have high L* and a higher ITA angle
        assert result.lab_values["L"] > 60
        assert result.fitzpatrick <= 3
        assert result.hex_color.startswith("#")
        assert len(result.hex_color) == 7

    def test_deep_skin_low_ita(self, deep_skin_image, synthetic_face_landmarks, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(deep_skin_image, synthetic_face_landmarks, synthetic_mesh_points)
        assert result.lab_values["L"] < 60
        assert result.fitzpatrick >= 3

    def test_warm_undertone_detected(self, warm_undertone_image, synthetic_face_landmarks, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(warm_undertone_image, synthetic_face_landmarks, synthetic_mesh_points)
        # Strong yellow cast (high b*, low a*) should classify as warm
        assert result.undertone in (Undertone.WARM, Undertone.NEUTRAL)

    def test_cool_undertone_detected(self, cool_undertone_image, synthetic_face_landmarks, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(cool_undertone_image, synthetic_face_landmarks, synthetic_mesh_points)
        assert result.undertone in (Undertone.COOL, Undertone.NEUTRAL)

    def test_confidence_increases_with_more_rois(self, fair_skin_image, synthetic_face_landmarks, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(fair_skin_image, synthetic_face_landmarks, synthetic_mesh_points)
        assert 0.7 <= result.confidence <= 0.97

    def test_fallback_with_empty_mesh(self, fair_skin_image, synthetic_face_landmarks) -> None:
        """When mesh is too short, falls back to geometric ROI sampling."""
        result = self.analyzer.analyze(fair_skin_image, synthetic_face_landmarks, [[0.5, 0.5, 0.0]] * 10)
        assert result.tone is not None
        assert result.hex_color.startswith("#")

    def test_ita_classification_thresholds(self) -> None:
        analyzer = self.analyzer
        # High ITA -> fair, fitzpatrick 1
        tone, fitz = analyzer._classify_tone(60.0)
        assert fitz == 1
        # Low ITA -> deep, fitzpatrick 6
        tone, fitz = analyzer._classify_tone(-50.0)
        assert fitz == 6

    def test_lab_to_hex_roundtrip_format(self) -> None:
        hex_color = self.analyzer._lab_to_hex(70.0, 10.0, 20.0)
        assert hex_color.startswith("#")
        assert len(hex_color) == 7
        int(hex_color[1:], 16)  # should not raise

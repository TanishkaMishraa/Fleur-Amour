"""
Unit tests — DarkCircleAnalyzer.
Verifies ΔL* (luminance delta) based detection: a darker under-eye band
relative to cheek reference triggers detection with a category matching
the severity thresholds; a uniform face does not.
"""
from __future__ import annotations

import numpy as np

from app.pipeline.analyzers.dark_circle_analyzer import DarkCircleAnalyzer


class TestDarkCircleAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = DarkCircleAnalyzer()

    def test_detects_dark_circles(self, dark_circle_face_image, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(dark_circle_face_image, synthetic_mesh_points)
        assert result.detected is True
        assert result.lab_delta > 0
        assert result.category in {"mild", "moderate", "severe"}
        assert 0.0 <= result.severity <= 1.0

    def test_uniform_face_no_dark_circles(self, no_dark_circle_face_image, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(no_dark_circle_face_image, synthetic_mesh_points)
        assert result.detected is False
        assert result.category == "none"
        assert result.severity == 0.0

    def test_severity_increases_with_delta(self, synthetic_mesh_points) -> None:
        size = 400
        mild = np.full((size, size, 3), (180, 175, 190), dtype=np.uint8)
        mild[int(size*0.42):int(size*0.49), :] = (140, 135, 150)  # small delta

        severe = np.full((size, size, 3), (180, 175, 190), dtype=np.uint8)
        severe[int(size*0.42):int(size*0.49), :] = (40, 35, 50)   # large delta

        mild_result = self.analyzer.analyze(mild, synthetic_mesh_points)
        severe_result = self.analyzer.analyze(severe, synthetic_mesh_points)

        assert severe_result.lab_delta > mild_result.lab_delta
        assert severe_result.severity >= mild_result.severity

    def test_handles_empty_roi_gracefully(self) -> None:
        """A mesh with insufficient points falls back to geometric ROI sampling."""
        small_mesh = [[0.5, 0.5, 0.0]] * 10
        img = np.full((400, 400, 3), (150, 150, 150), dtype=np.uint8)
        result = self.analyzer.analyze(img, small_mesh)
        assert result.category in {"none", "mild", "moderate", "severe"}
        assert 0.0 <= result.severity <= 1.0

    def test_vascularity_flag_is_boolean(self, dark_circle_face_image, synthetic_mesh_points) -> None:
        result = self.analyzer.analyze(dark_circle_face_image, synthetic_mesh_points)
        assert isinstance(result.vascularity, bool)

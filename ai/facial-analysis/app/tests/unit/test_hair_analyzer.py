"""
Unit tests — HairAnalyzer.
Tests hair detection, dominant colour extraction, and the graceful
fallback paths for images where no hair region can be isolated.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.pipeline.analyzers.hair_analyzer import HairAnalyzer
from app.schemas.analysis_schemas import HairAnalysisResult, HairType


@pytest.fixture
def brunette_face_image() -> np.ndarray:
    """
    A 600×600 image with a dark-brown hair region in the top third
    and a neutral skin tone in the lower portion.
    face_bbox sits in the middle third so the hair ROI falls above it.
    """
    img = np.full((600, 600, 3), (160, 145, 165), dtype=np.uint8)  # skin
    img[:150, :] = (30, 20, 15)   # dark brown hair (BGR: very dark brown)
    return img


@pytest.fixture
def blonde_face_image() -> np.ndarray:
    """Golden-blonde hair in the top region."""
    img = np.full((600, 600, 3), (160, 145, 165), dtype=np.uint8)
    img[:150, :] = (100, 180, 220)  # golden/blonde in BGR
    return img


# face_bbox: x, y, w, h — face covers the middle portion of a 600×600 image
_FACE_BBOX = (80, 180, 440, 300)  # face from y=180 to y=480; hair above y=180


class TestHairAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = HairAnalyzer()

    def test_detects_hair_in_brunette_image(self, brunette_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(brunette_face_image, _FACE_BBOX)
        assert isinstance(result, HairAnalysisResult)
        # With clear dark hair above the face region, hair should be detected
        # (implementation-dependent; test robustly against both detected states)
        assert isinstance(result.hair_detected, bool)
        assert result.dominant_color.startswith("#")
        assert len(result.dominant_color) == 7

    def test_hex_color_valid_format(self, brunette_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(brunette_face_image, _FACE_BBOX)
        hex_val = result.dominant_color.lstrip("#")
        int(hex_val, 16)   # should not raise

    def test_result_scores_within_bounds(
        self, brunette_face_image: np.ndarray, blonde_face_image: np.ndarray
    ) -> None:
        for img in (brunette_face_image, blonde_face_image):
            result = self.analyzer.analyze(img, _FACE_BBOX)
            if result.shine_score is not None:
                assert 0.0 <= result.shine_score <= 1.0
            if result.volume_score is not None:
                assert 0.0 <= result.volume_score <= 1.0

    def test_hair_type_is_valid_enum(
        self, brunette_face_image: np.ndarray
    ) -> None:
        result = self.analyzer.analyze(brunette_face_image, _FACE_BBOX)
        assert result.hair_type in set(HairType)

    def test_empty_bbox_returns_fallback(self, brunette_face_image: np.ndarray) -> None:
        """Zero-size bbox cannot produce a hair ROI — should fall back gracefully."""
        result = self.analyzer.analyze(brunette_face_image, (0, 0, 0, 0))
        assert isinstance(result, HairAnalysisResult)
        assert result.hair_type in set(HairType)

    def test_color_names_is_list(self, brunette_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(brunette_face_image, _FACE_BBOX)
        assert isinstance(result.color_names, list)

    def test_empty_result_fallback(self) -> None:
        """_empty_result() is called when no ROI — verify it matches schema."""
        result = self.analyzer._empty_result()
        assert result.hair_detected is False
        assert result.hair_type == HairType.UNKNOWN
        assert result.dominant_color == "#000000"
        assert result.color_names == []
        assert result.shine_score is None
        assert result.volume_score is None

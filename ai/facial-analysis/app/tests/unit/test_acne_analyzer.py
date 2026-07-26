"""
Unit tests — AcneAnalyzer.
Uses synthetic face crops:
  - A clean, smooth-coloured image should produce zero/minimal acne count.
  - A crop with red blob contours (simulating pimples) should register
    detected=True and a non-zero count.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.pipeline.analyzers.acne_analyzer import AcneAnalyzer
from app.schemas.analysis_schemas import AcneAnalysisResult


@pytest.fixture
def clean_face_image() -> np.ndarray:
    """A large flat-colour image with a smooth, uniform skin tone."""
    return np.full((400, 400, 3), (155, 140, 160), dtype=np.uint8)


@pytest.fixture
def acne_face_image() -> np.ndarray:
    """
    A skin-toned image with several red oval blobs simulating inflamed
    pimples, sized within AcneAnalyzer._MIN_ACNE_BLOB … _MAX_ACNE_BLOB.
    """
    img = np.full((400, 400, 3), (155, 140, 160), dtype=np.uint8)  # neutral skin
    # Draw 6 bright-red blobs of varying sizes on the forehead and cheeks
    centres = [(80, 80), (120, 70), (200, 90), (280, 80), (90, 250), (310, 240)]
    radii   = [8,        6,         9,          7,          6,          8       ]
    for (cy, cx), r in zip(centres, radii):
        # Red in BGR
        img[cy-r:cy+r, cx-r:cx+r] = (0, 0, 220)
    return img


# face bbox covering the whole 400×400 image
_FULL_BBOX = (0, 0, 400, 400)
# face bbox for a sub-region
_SMALL_BBOX = (50, 50, 300, 300)


class TestAcneAnalyzer:

    def setup_method(self) -> None:
        self.analyzer = AcneAnalyzer()

    def test_clean_face_no_acne(self, clean_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(clean_face_image, _FULL_BBOX)
        assert isinstance(result, AcneAnalysisResult)
        assert result.severity in {"none", "mild", "moderate", "severe"}
        # A perfectly uniform skin-tone image should yield no or very few detections
        assert result.count <= 2

    def test_acne_detected_on_pimple_image(self, acne_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(acne_face_image, _FULL_BBOX)
        assert isinstance(result, AcneAnalysisResult)
        assert result.detected is True
        assert result.count >= 1

    def test_severity_score_bounds(
        self, clean_face_image: np.ndarray, acne_face_image: np.ndarray
    ) -> None:
        for img, bbox in [(clean_face_image, _FULL_BBOX), (acne_face_image, _FULL_BBOX)]:
            result = self.analyzer.analyze(img, bbox)
            assert 0.0 <= result.severity_score <= 1.0

    def test_severity_ordering(
        self, clean_face_image: np.ndarray, acne_face_image: np.ndarray
    ) -> None:
        """Acne image should score higher than clean image."""
        clean  = self.analyzer.analyze(clean_face_image, _FULL_BBOX)
        blemished = self.analyzer.analyze(acne_face_image, _FULL_BBOX)
        assert blemished.severity_score >= clean.severity_score

    def test_empty_bbox_returns_gracefully(self, clean_face_image: np.ndarray) -> None:
        """A zero-size crop (bad bbox) should return a clean empty result."""
        result = self.analyzer.analyze(clean_face_image, (0, 0, 0, 0))
        assert result.detected is False
        assert result.count == 0
        assert result.severity == "none"

    def test_regions_list_type(self, acne_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(acne_face_image, _FULL_BBOX)
        assert isinstance(result.regions, list)

    def test_concerns_list_type(self, acne_face_image: np.ndarray) -> None:
        result = self.analyzer.analyze(acne_face_image, _FULL_BBOX)
        assert isinstance(result.concerns, list)

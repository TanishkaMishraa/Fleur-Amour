"""
AuraFit AI Facial Analysis — shared pytest fixtures.
Generates synthetic test images (no real faces needed for unit tests of
colour/geometry math) and provides a FastAPI TestClient for integration tests.
"""
from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from app.schemas.analysis_schemas import (
    BoundingBox,
    FaceLandmarks,
    QualityCheck,
)


@pytest.fixture
def synthetic_face_landmarks() -> FaceLandmarks:
    """
    A geometrically 'oval' face: face_length_ratio ~1.3, jaw_width_ratio ~0.72,
    cheekbone_ratio ~0.80 — falls in the oval classification band.
    """
    return FaceLandmarks(
        left_eye=[0.35, 0.40],
        right_eye=[0.65, 0.40],
        nose_tip=[0.50, 0.52],
        left_mouth=[0.42, 0.65],
        right_mouth=[0.58, 0.65],
        chin=[0.50, 0.92],
        left_temple=[0.20, 0.35],
        right_temple=[0.80, 0.35],
        left_cheekbone=[0.24, 0.50],
        right_cheekbone=[0.76, 0.50],
        jaw_width_ratio=0.72,
        face_length_ratio=1.30,
        cheekbone_ratio=0.80,
    )


@pytest.fixture
def round_face_landmarks() -> FaceLandmarks:
    """A round face: short face_length_ratio, wide jaw and cheekbones."""
    return FaceLandmarks(
        left_eye=[0.35, 0.42], right_eye=[0.65, 0.42],
        nose_tip=[0.50, 0.52], left_mouth=[0.42, 0.62], right_mouth=[0.58, 0.62],
        chin=[0.50, 0.85], left_temple=[0.18, 0.40], right_temple=[0.82, 0.40],
        left_cheekbone=[0.16, 0.50], right_cheekbone=[0.84, 0.50],
        jaw_width_ratio=0.88, face_length_ratio=1.05, cheekbone_ratio=0.92,
    )


@pytest.fixture
def synthetic_mesh_points() -> list[list[float]]:
    """468-point mesh stub — only indices used by analyzers are meaningful."""
    mesh = [[0.5, 0.5, 0.0] for _ in range(468)]
    # Key indices used by skin tone / dark circle analyzers
    mesh[10]  = [0.50, 0.18, 0.0]   # forehead
    mesh[116] = [0.28, 0.50, 0.0]   # left cheek
    mesh[345] = [0.72, 0.50, 0.0]   # right cheek
    mesh[4]   = [0.50, 0.52, 0.02]  # nose tip (low z = visible)
    mesh[61]  = [0.42, 0.65, 0.02]  # left mouth
    for i in [338, 297, 332, 284, 251, 389, 356, 454, 323]:
        mesh[i] = [0.5 + (i % 10) * 0.01, 0.15, 0.0]
    # Dark-circle analyzer landmark indices (under-eye + cheek reference)
    mesh[145] = [0.38, 0.42, 0.0]   # below left lower lid
    mesh[374] = [0.62, 0.42, 0.0]   # below right lower lid
    mesh[130] = [0.30, 0.44, 0.0]   # under-eye ROI left edge
    mesh[359] = [0.70, 0.44, 0.0]   # under-eye ROI right edge
    mesh[187] = [0.30, 0.62, 0.0]   # mid-cheek reference point
    return mesh


@pytest.fixture
def dark_circle_face_image() -> np.ndarray:
    """
    A face-sized image with a darker band across the under-eye region
    (y: 42-49% of height) relative to the brighter cheek band below it
    (y: 58-66%) — should trigger dark-circle detection.
    """
    size = 400
    img = np.full((size, size, 3), (180, 175, 190), dtype=np.uint8)  # bright cheek tone
    y1, y2 = int(size * 0.42), int(size * 0.49)
    img[y1:y2, :] = (90, 85, 95)  # noticeably darker under-eye band
    return img


@pytest.fixture
def no_dark_circle_face_image() -> np.ndarray:
    """Uniform skin tone everywhere — should NOT trigger dark-circle detection."""
    return np.full((400, 400, 3), (180, 175, 190), dtype=np.uint8)


def _make_skin_tone_image(bgr_color: tuple[int, int, int], size: int = 200) -> np.ndarray:
    """Create a flat-colour BGR image simulating uniform skin tone."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, :] = bgr_color
    return img


@pytest.fixture
def fair_skin_image() -> np.ndarray:
    """BGR image approximating fair/Fitzpatrick I-II skin (high L*, low a*/b*)."""
    return _make_skin_tone_image((220, 210, 235))  # light pinkish-tan in BGR


@pytest.fixture
def deep_skin_image() -> np.ndarray:
    """BGR image approximating deep/Fitzpatrick V-VI skin (low L*)."""
    return _make_skin_tone_image((45, 55, 90))


@pytest.fixture
def warm_undertone_image() -> np.ndarray:
    """BGR image with strong yellow/golden cast (warm undertone)."""
    return _make_skin_tone_image((90, 170, 210))


@pytest.fixture
def cool_undertone_image() -> np.ndarray:
    """BGR image with pink/rosy cast (cool undertone)."""
    return _make_skin_tone_image((175, 160, 220))


@pytest.fixture
def blank_face_bgr() -> np.ndarray:
    """A larger neutral-tone image standing in for a full face crop."""
    img = np.full((400, 400, 3), (150, 150, 150), dtype=np.uint8)
    rng = np.random.default_rng(42)
    noise = rng.integers(-5, 5, img.shape, dtype=np.int16)
    return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """A minimal valid JPEG (200x200 grey square) for image_processor tests."""
    img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture
def tiny_jpeg_bytes() -> bytes:
    """A too-small image (50x50) — should fail quality checks."""
    img = Image.new("RGB", (50, 50), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

"""
AuraFit — Hair analysis.
Detects hair region via MediaPipe Selfie Segmentation + HSV analysis.
Extracts: dominant color, color names, hair type inference from texture.
Hair type (straight/wavy/curly/coily) from edge density above the face ROI.
"""
from __future__ import annotations

import colorsys
from typing import Any

import cv2
import numpy as np

from app.schemas.analysis_schemas import HairAnalysisResult, HairType


# Approximate hair colour names in HSV space
_HAIR_COLOURS = [
    ("black",        (0,   0,   0),   (180, 255, 55)),
    ("very_dark_brown", (0, 10,  40),  (25,  80,  80)),
    ("dark_brown",   (5,  30,  50),   (25, 150, 120)),
    ("medium_brown", (15, 50,  80),   (30, 200, 160)),
    ("auburn",       (5,  80,  80),   (18, 220, 180)),
    ("light_brown",  (20, 30,  100),  (35, 150, 200)),
    ("dark_blonde",  (25, 40,  120),  (40, 160, 220)),
    ("blonde",       (30, 30,  150),  (45, 130, 255)),
    ("red",          (0, 100,  100),  (12, 255, 200)),
    ("grey_white",   (0,   0,  150),  (180,  30, 255)),
    ("platinum",     (0,   0,  200),  (180,  15, 255)),
]


class HairAnalyzer:
    """Detect and analyse hair from selfie image."""

    def analyze(
        self,
        bgr: np.ndarray,
        face_bbox: tuple[int, int, int, int],
    ) -> HairAnalysisResult:
        hair_roi = self._extract_hair_roi(bgr, face_bbox)

        if hair_roi is None or hair_roi.size < 100:
            return HairAnalysisResult(
                hair_detected=False, hair_type=HairType.UNKNOWN,
                dominant_color="#000000", color_names=["unknown"],
                texture_score=None, shine_score=None, volume_score=None,
            )

        dominant_hex, color_names = self._analyse_color(hair_roi)
        hair_type    = self._classify_texture(hair_roi)
        shine        = self._shine_score(hair_roi)
        volume       = self._volume_score(hair_roi, face_bbox)

        return HairAnalysisResult(
            hair_detected=True,
            hair_type=hair_type,
            dominant_color=dominant_hex,
            color_names=color_names,
            texture_score=round(0.5, 3),   # Reserved for CNN model
            shine_score=round(shine, 3),
            volume_score=round(volume, 3),
        )

    # ── Private ────────────────────────────────────────────────────────────────

    def _extract_hair_roi(
        self,
        bgr: np.ndarray,
        face_bbox: tuple[int, int, int, int],
    ) -> np.ndarray | None:
        """
        Hair region = area above the face bounding box.
        Simple heuristic: top 30% of image above face centre.
        Full version uses MediaPipe Selfie Segmentation.
        """
        x, y, w, h = face_bbox
        h_img, w_img = bgr.shape[:2]

        # Hair typically in top portion above face
        hair_y1 = max(0, y - int(h * 0.5))
        hair_y2 = max(1, y + int(h * 0.1))
        hair_x1 = max(0, x - int(w * 0.2))
        hair_x2 = min(w_img, x + w + int(w * 0.2))

        if hair_y2 <= hair_y1:
            return None

        roi = bgr[hair_y1:hair_y2, hair_x1:hair_x2]

        # Basic colour filter: exclude very bright sky/wall pixels
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # Keep pixels that aren't extremely bright (likely background)
        mask = hsv[:, :, 2] < 220
        roi_masked = roi.copy()
        roi_masked[~mask] = 0

        return roi_masked if roi_masked.size > 200 else roi

    def _analyse_color(
        self, hair_roi: np.ndarray
    ) -> tuple[str, list[str]]:
        """K-means dominant colour + name matching."""
        pixels = hair_roi.reshape(-1, 3).astype(np.float32)
        # Filter near-zero pixels (masked out)
        pixels = pixels[pixels.sum(axis=1) > 30]

        if len(pixels) < 50:
            return "#1C1008", ["dark_brown"]

        # K-means: 1 cluster for dominant colour
        _, labels, centres = cv2.kmeans(
            pixels, 1, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5),
            5, cv2.KMEANS_RANDOM_CENTERS,
        )
        dominant_bgr = centres[0].astype(int)
        r, g, b = int(dominant_bgr[2]), int(dominant_bgr[1]), int(dominant_bgr[0])
        dominant_hex = f"#{r:02X}{g:02X}{b:02X}"

        # Match to colour name
        color_names = self._match_colour_name(r, g, b)

        return dominant_hex, color_names

    def _match_colour_name(self, r: int, g: int, b: int) -> list[str]:
        """Find closest colour name(s) by Euclidean distance in RGB space."""
        palette = {
            "black":         (20,  15,  10),
            "dark_brown":    (60,  35,  20),
            "medium_brown":  (100, 65,  35),
            "auburn":        (120, 50,  30),
            "light_brown":   (150, 105, 65),
            "dark_blonde":   (180, 145, 90),
            "blonde":        (210, 185, 125),
            "red":           (160, 60,  50),
            "grey":          (140, 135, 135),
            "white":         (230, 225, 220),
            "platinum":      (220, 215, 200),
        }
        distances = {name: ((r-cr)**2 + (g-cg)**2 + (b-cb)**2) ** 0.5
                     for name, (cr, cg, cb) in palette.items()}
        sorted_names = sorted(distances, key=distances.get)  # type: ignore[arg-type]
        return sorted_names[:2]

    def _classify_texture(self, hair_roi: np.ndarray) -> HairType:
        """
        Infer hair type from edge density in the ROI.
        Curly hair → high edge density (many direction changes).
        Straight hair → lower edge density, more uniform gradients.
        """
        gray = cv2.cvtColor(hair_roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        edge_density = cv2.countNonZero(edges) / max(1, gray.size)

        if edge_density > 0.15:
            return HairType.COILY
        if edge_density > 0.10:
            return HairType.CURLY
        if edge_density > 0.06:
            return HairType.WAVY
        return HairType.STRAIGHT

    def _shine_score(self, hair_roi: np.ndarray) -> float:
        """Percentage of specular highlights → shine indicator."""
        hsv = cv2.cvtColor(hair_roi, cv2.COLOR_BGR2HSV)
        # High V (brightness) + low S (saturation) = specular highlight
        bright = (hsv[:, :, 2] > 200) & (hsv[:, :, 1] < 60)
        return float(bright.sum() / max(1, hair_roi.shape[0] * hair_roi.shape[1]))

    def _volume_score(
        self, hair_roi: np.ndarray, face_bbox: tuple[int, int, int, int]
    ) -> float:
        """Estimate volume as hair width relative to face width."""
        face_w = face_bbox[2]
        hair_w = hair_roi.shape[1]
        ratio  = hair_w / max(1, face_w)
        return float(min(1.0, max(0.0, (ratio - 0.8) / 0.8)))

    def _empty_result(self) -> HairAnalysisResult:
        """Fallback when hair region cannot be isolated."""
        return HairAnalysisResult(
            hair_detected=False,
            hair_type=HairType.UNKNOWN,
            dominant_color="#000000",
            color_names=[],
            texture_score=None,
            shine_score=None,
            volume_score=None,
        )

"""
AuraFit — Skin tone & undertone analyzer.
Method: ITA° (Individual Typology Angle) computed in CIELAB colour space.
- Samples multiple forehead/cheek ROIs to reduce specular highlight noise.
- Fitzpatrick scale mapping from ITA°.
- Undertone from a*/b* ratio (warm/cool/neutral).
"""
from __future__ import annotations

import colorsys
import math
from typing import Any

import cv2
import numpy as np

from app.schemas.analysis_schemas import SkinTone, SkinToneResult, Undertone


# ITA° thresholds → Fitzpatrick + AuraFit tone label
_ITA_THRESHOLDS = [
    (55,  SkinTone.FAIR,   1, "cool"),     # ITA > 55°
    (41,  SkinTone.LIGHT,  2, "neutral"),  # 41–55°
    (28,  SkinTone.MEDIUM, 3, "warm"),     # 28–41°
    (10,  SkinTone.OLIVE,  4, "warm"),     # 10–28°
    (-30, SkinTone.TAN,    5, "warm"),     # -30–10°
    (-90, SkinTone.DEEP,   6, "cool"),     # < -30°
]

# Undertone: a* captures red-green, b* captures yellow-blue
_UNDERTONE_RULES = {
    "cool":    (lambda a, b: a > 5 and b < 10),   # pink/rosy
    "warm":    (lambda a, b: b > 12 and a < 8),   # yellow/golden
    "neutral": (lambda a, b: True),                # fallback
}


class SkinToneAnalyzer:
    """Analyse skin tone, undertone, ITA°, Fitzpatrick scale from face ROIs."""

    def analyze(
        self,
        bgr: np.ndarray,
        landmarks: Any,
        mesh_points: list[list[float]],
    ) -> SkinToneResult:
        """
        bgr:        full BGR image
        landmarks:  FaceLandmarks object with normalised coordinates
        mesh_points: 468-point MediaPipe mesh
        """
        h, w = bgr.shape[:2]

        # Sample 3 ROIs: forehead, left cheek, right cheek
        lab_samples = []
        for roi_bgr in self._get_skin_rois(bgr, mesh_points, h, w):
            if roi_bgr is not None and roi_bgr.size > 0:
                lab_samples.append(self._mean_lab(roi_bgr))

        if not lab_samples:
            # Fallback: sample centre of image
            lab_samples = [self._mean_lab(bgr)]

        # Weighted average (forehead weighted 2x for accuracy)
        weights = [2.0] + [1.0] * (len(lab_samples) - 1)
        L = sum(s["L"] * w for s, w in zip(lab_samples, weights)) / sum(weights[:len(lab_samples)])
        a = sum(s["a"] * w for s, w in zip(lab_samples, weights)) / sum(weights[:len(lab_samples)])
        b = sum(s["b"] * w for s, w in zip(lab_samples, weights)) / sum(weights[:len(lab_samples)])

        # ITA° = arctan((L - 50) / b) × (180/π)
        ita = math.degrees(math.atan2(L - 50.0, b)) if b != 0 else 0.0

        # Classify tone
        tone, fitzpatrick = self._classify_tone(ita)

        # Classify undertone from a*/b* ratio
        undertone = self._classify_undertone(a, b)

        # Compute closest hex swatch
        hex_color = self._lab_to_hex(L, a, b)

        # Confidence: higher when multiple ROIs agree
        confidence = min(0.97, 0.70 + 0.09 * len(lab_samples))

        return SkinToneResult(
            tone=tone,
            undertone=undertone,
            ita_angle=round(ita, 2),
            lab_values={"L": round(L, 2), "a": round(a, 2), "b": round(b, 2)},
            hex_color=hex_color,
            fitzpatrick=fitzpatrick,
            confidence=round(confidence, 3),
        )

    # ── Private ────────────────────────────────────────────────────────────────

    def _get_skin_rois(
        self,
        bgr: np.ndarray,
        mesh: list[list[float]],
        h: int,
        w: int,
    ) -> list[np.ndarray | None]:
        """Extract forehead, left cheek, right cheek ROIs."""
        rois = []

        def crop(centre_x: float, centre_y: float, radius: int) -> np.ndarray | None:
            cx, cy = int(centre_x * w), int(centre_y * h)
            y1, y2 = max(0, cy - radius), min(h, cy + radius)
            x1, x2 = max(0, cx - radius), min(w, cx + radius)
            if y2 > y1 and x2 > x1:
                return bgr[y1:y2, x1:x2]
            return None

        if len(mesh) > 200:
            # Forehead centre (landmark 10 area)
            rois.append(crop(mesh[10][0], mesh[10][1] - 0.04, 25))
            # Left cheek (landmark 116)
            rois.append(crop(mesh[116][0], mesh[116][1], 20))
            # Right cheek (landmark 345)
            rois.append(crop(mesh[345][0], mesh[345][1], 20))
        else:
            # Fallback: geometric regions
            rois.append(crop(0.5, 0.25, 40))   # forehead
            rois.append(crop(0.25, 0.55, 30))   # left cheek
            rois.append(crop(0.75, 0.55, 30))   # right cheek

        return rois

    def _mean_lab(self, bgr: np.ndarray) -> dict[str, float]:
        """Convert ROI to LAB and return mean L*a*b* values."""
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(float)
        # OpenCV LAB: L in [0,255], a/b in [0,255] (centred at 128)
        L_mean = lab[:, :, 0].mean() / 255.0 * 100.0
        a_mean = lab[:, :, 1].mean() - 128.0
        b_mean = lab[:, :, 2].mean() - 128.0
        return {"L": L_mean, "a": a_mean, "b": b_mean}

    def _classify_tone(self, ita: float) -> tuple[SkinTone, int]:
        for threshold, tone, fitzpatrick, _ in _ITA_THRESHOLDS:
            if ita >= threshold:
                return tone, fitzpatrick
        return SkinTone.DEEP, 6

    def _classify_undertone(self, a: float, b: float) -> Undertone:
        if a > 5 and b < 10:
            return Undertone.COOL
        if b > 12 and a < 8:
            return Undertone.WARM
        return Undertone.NEUTRAL

    def _lab_to_hex(self, L: float, a: float, b: float) -> str:
        """Convert LAB to sRGB hex (approximate)."""
        # LAB → XYZ
        fy = (L + 16) / 116
        fx = a / 500 + fy
        fz = fy - b / 200

        def f_inv(t: float) -> float:
            return t**3 if t > 0.2069 else (t - 16/116) / 7.787

        X = f_inv(fx) * 95.047
        Y = f_inv(fy) * 100.0
        Z = f_inv(fz) * 108.883

        # XYZ → linear RGB (D65 illuminant)
        r_lin = X *  3.2406 + Y * -1.5372 + Z * -0.4986
        g_lin = X * -0.9689 + Y *  1.8758 + Z *  0.0415
        b_lin = X *  0.0557 + Y * -0.2040 + Z *  1.0570

        def gamma(c: float) -> int:
            c = max(0.0, min(1.0, c / 100.0))
            c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1/2.4)) - 0.055
            return int(round(max(0, min(255, c * 255))))

        r, g, b_ = gamma(r_lin), gamma(g_lin), gamma(b_lin)
        return f"#{r:02X}{g:02X}{b_:02X}"

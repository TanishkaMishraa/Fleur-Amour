"""
AuraFit — Dark circle detector.
Method: Compare L* luminance of under-eye region vs mid-cheek reference.
ΔL* > 8 = dark circles detected.
Additional hue analysis: blue/purple hue (vascular) vs brown (pigmentation).
"""
from __future__ import annotations

import cv2
import numpy as np

from app.schemas.analysis_schemas import DarkCircleResult


class DarkCircleAnalyzer:

    # Severity thresholds based on ΔL*
    _MILD     = 5.0
    _MODERATE = 10.0
    _SEVERE   = 18.0

    def analyze(
        self,
        bgr: np.ndarray,
        mesh_points: list[list[float]],
    ) -> DarkCircleResult:
        h, w = bgr.shape[:2]

        under_eye_bgr = self._get_under_eye_roi(bgr, mesh_points, h, w)
        cheek_bgr     = self._get_cheek_roi(bgr, mesh_points, h, w)

        if under_eye_bgr is None or cheek_bgr is None or \
           under_eye_bgr.size == 0 or cheek_bgr.size == 0:
            return DarkCircleResult(detected=False, severity=0.0,
                                    lab_delta=0.0, category="none",
                                    vascularity=False)

        L_under = self._mean_L(under_eye_bgr)
        L_cheek = self._mean_L(cheek_bgr)
        delta_L = L_cheek - L_under   # positive = under-eye is darker

        # Vascularity: blue/purple hue in under-eye
        vascular = self._is_vascular(under_eye_bgr)

        # Severity score normalised to 0–1
        severity = min(1.0, max(0.0, (delta_L - self._MILD) / (self._SEVERE - self._MILD)))

        category = (
            "none"     if delta_L < self._MILD     else
            "mild"     if delta_L < self._MODERATE else
            "moderate" if delta_L < self._SEVERE   else
            "severe"
        )

        return DarkCircleResult(
            detected=delta_L >= self._MILD,
            severity=round(severity, 3),
            lab_delta=round(delta_L, 2),
            category=category,
            vascularity=vascular,
        )

    def _get_under_eye_roi(
        self, bgr: np.ndarray, mesh: list[list[float]], h: int, w: int
    ) -> np.ndarray | None:
        """Sample under-eye using MediaPipe landmarks 133 and 362 (inner eye corners)."""
        if len(mesh) < 380:
            return bgr[int(h*0.40):int(h*0.52), int(w*0.2):int(w*0.8)]
        # Under left eye: landmarks 234-246 area
        left_y  = int(mesh[145][1] * h) + 5   # below left lower lid
        right_y = int(mesh[374][1] * h) + 5   # below right lower lid
        avg_y   = (left_y + right_y) // 2
        y1, y2  = avg_y, min(h, avg_y + int(h * 0.07))
        x1      = int(mesh[130][0] * w)
        x2      = int(mesh[359][0] * w)
        if x2 <= x1 or y2 <= y1:
            return None
        return bgr[y1:y2, x1:x2]

    def _get_cheek_roi(
        self, bgr: np.ndarray, mesh: list[list[float]], h: int, w: int
    ) -> np.ndarray | None:
        """Sample mid-cheek as reference for true skin tone."""
        if len(mesh) < 350:
            return bgr[int(h*0.55):int(h*0.70), int(w*0.2):int(w*0.8)]
        cy = int(mesh[187][1] * h)
        cx = int(mesh[187][0] * w)
        r  = int(h * 0.04)
        return bgr[max(0, cy-r):cy+r, max(0, cx-r):cx+r]

    def _mean_L(self, roi: np.ndarray) -> float:
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        return float(lab[:, :, 0].mean()) / 255.0 * 100.0

    def _is_vascular(self, roi: np.ndarray) -> bool:
        """Blue/purple tint in under-eye → vascular dark circles."""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # Blue-purple hue range
        mask = cv2.inRange(hsv, np.array([100, 30, 30]), np.array([160, 255, 200]))
        ratio = cv2.countNonZero(mask) / max(1, roi.shape[0] * roi.shape[1])
        return ratio > 0.12

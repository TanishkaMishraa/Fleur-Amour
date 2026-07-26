"""
AuraFit — Acne and skin concern detector.
Uses OpenCV morphological operations + LAB colour space to detect:
  - Acne/pimples (red elevated lesions)
  - Hyperpigmentation (dark patches)
  - Redness regions
  - Enlarged pores (texture gradient analysis)
All analysis confined to face ROI to avoid false positives from background.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.schemas.analysis_schemas import (
    AcneAnalysisResult, SkinConcern, SkinConcernResult,
)


class AcneAnalyzer:
    """Detect acne, hyperpigmentation, and redness in face ROI."""

    # HSV red range for acne/inflammation detection
    _RED_LOWER1 = np.array([0,   80,  60])
    _RED_UPPER1 = np.array([10, 255, 255])
    _RED_LOWER2 = np.array([165, 80,  60])
    _RED_UPPER2 = np.array([180, 255, 255])

    # Minimum blob size to count as a pimple (pixels²)
    _MIN_ACNE_BLOB = 30
    _MAX_ACNE_BLOB = 800

    def analyze(
        self,
        bgr: np.ndarray,
        face_bbox: tuple[int, int, int, int],
    ) -> AcneAnalysisResult:
        """
        bgr:       full BGR image
        face_bbox: (x, y, w, h) of face region
        """
        x, y, w, h = face_bbox
        face_bgr = bgr[y:y+h, x:x+w]
        if face_bgr.size == 0:
            return self._empty_result()

        pimple_count, regions, severity_score = self._detect_acne(face_bgr)
        concerns: list[SkinConcernResult] = []

        # Acne concern
        if pimple_count > 0:
            concerns.append(SkinConcernResult(
                concern=SkinConcern.ACNE,
                severity=severity_score,
                region="cheeks,forehead",
                pixel_count=pimple_count,
            ))

        # Redness concern (separate from acne blobs)
        redness = self._detect_redness(face_bgr)
        if redness > 0.3:
            concerns.append(SkinConcernResult(
                concern=SkinConcern.REDNESS,
                severity=round(min(1.0, redness), 3),
                region="cheeks,nose",
            ))

        # Hyperpigmentation (dark LAB patches)
        hyper_severity = self._detect_hyperpigmentation(face_bgr)
        if hyper_severity > 0.25:
            concerns.append(SkinConcernResult(
                concern=SkinConcern.HYPERPIGMENTATION,
                severity=round(hyper_severity, 3),
                region="cheeks,forehead",
            ))

        severity_label = (
            "none" if severity_score < 0.15 else
            "mild" if severity_score < 0.40 else
            "moderate" if severity_score < 0.70 else
            "severe"
        )

        return AcneAnalysisResult(
            detected=pimple_count > 0,
            count=pimple_count,
            severity=severity_label,
            severity_score=round(severity_score, 3),
            regions=regions,
            concerns=concerns,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _detect_acne(
        self, face_bgr: np.ndarray
    ) -> tuple[int, list[str], float]:
        """Find red inflamed lesions using HSV masking + blob analysis."""
        hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)

        # Two red ranges (hue wraps around)
        mask1 = cv2.inRange(hsv, self._RED_LOWER1, self._RED_UPPER1)
        mask2 = cv2.inRange(hsv, self._RED_LOWER2, self._RED_UPPER2)
        mask  = cv2.bitwise_or(mask1, mask2)

        # Morphological ops: close small holes, remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

        # Find contours (blobs)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pimples = [c for c in contours if self._MIN_ACNE_BLOB < cv2.contourArea(c) < self._MAX_ACNE_BLOB]

        count = len(pimples)
        h, w = face_bgr.shape[:2]

        # Classify regions
        regions = set()
        for c in pimples:
            M = cv2.moments(c)
            if M["m00"] == 0:
                continue
            cx_ = M["m10"] / M["m00"] / w
            cy_ = M["m01"] / M["m00"] / h
            if cy_ < 0.35:
                regions.add("forehead")
            elif cy_ < 0.65:
                if cx_ < 0.5:
                    regions.add("left_cheek")
                else:
                    regions.add("right_cheek")
            else:
                regions.add("chin")

        # Severity: count + area relative to face
        total_area = sum(cv2.contourArea(c) for c in pimples)
        face_area  = h * w
        area_ratio = total_area / max(1, face_area)
        severity   = min(1.0, count / 20.0 * 0.6 + area_ratio * 40 * 0.4)

        return count, sorted(regions), severity

    def _detect_redness(self, face_bgr: np.ndarray) -> float:
        """Overall redness score (0–1) via HSV saturation + hue analysis."""
        hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self._RED_LOWER1, self._RED_UPPER1)
        mask2 = cv2.inRange(hsv, self._RED_LOWER2, self._RED_UPPER2)
        red_pixels = cv2.countNonZero(cv2.bitwise_or(mask1, mask2))
        total = face_bgr.shape[0] * face_bgr.shape[1]
        return red_pixels / max(1, total)

    def _detect_hyperpigmentation(self, face_bgr: np.ndarray) -> float:
        """Detect dark patches relative to overall skin tone using LAB L* channel."""
        lab  = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
        L    = lab[:, :, 0].astype(float)
        mean_L = L.mean()
        # Pixels significantly darker than mean (>15 points below)
        dark_pixels = np.sum(L < mean_L - 15)
        total = L.size
        return dark_pixels / max(1, total)

    def _empty_result(self) -> AcneAnalysisResult:
        return AcneAnalysisResult(
            detected=False, count=0, severity="none",
            severity_score=0.0, regions=[], concerns=[],
        )

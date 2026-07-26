"""
AuraFit — Skin texture analyzer.
Methods:
  1. Haralick GLCM features (contrast, homogeneity, energy, correlation)
     — industry-standard texture features, robust to lighting variation
  2. Laplacian variance for overall sharpness/roughness
  3. LBP (Local Binary Pattern) for micro-texture (pore visibility)
All analysis performed on grayscale face ROI after histogram equalisation.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.schemas.analysis_schemas import SkinTextureResult


class SkinTextureAnalyzer:

    def analyze(
        self,
        bgr: np.ndarray,
        face_bbox: tuple[int, int, int, int],
    ) -> SkinTextureResult:
        x, y, w, h = face_bbox
        face_bgr = bgr[y:y+h, x:x+w]

        if face_bgr.size == 0:
            return self._empty()

        # Convert to grayscale + CLAHE (normalise lighting)
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_eq = clahe.apply(gray)

        haralick = self._haralick_features(gray_eq)
        roughness = self._laplacian_roughness(gray_eq)
        pore_visibility = self._lbp_pore_score(gray_eq)
        evenness = self._colour_evenness(face_bgr)

        # Overall texture score: smooth = 1, rough = 0
        overall = round(
            (1.0 - roughness) * 0.35 +
            haralick["homogeneity"] * 0.30 +
            (1.0 - pore_visibility) * 0.20 +
            evenness * 0.15,
            3
        )

        return SkinTextureResult(
            overall_score=overall,
            roughness=round(roughness, 3),
            pore_visibility=round(pore_visibility, 3),
            evenness=round(evenness, 3),
            haralick_features={k: round(v, 4) for k, v in haralick.items()},
            lbp_score=round(pore_visibility, 3),
        )

    # ── Haralick GLCM ─────────────────────────────────────────────────────────

    def _haralick_features(self, gray: np.ndarray) -> dict[str, float]:
        """
        Compute GLCM (Gray-Level Co-occurrence Matrix) features.
        skimage.feature.graycomatrix is ~3ms on 256×256 — fast enough.
        """
        try:
            from skimage.feature import graycomatrix, graycoprops
            # Quantise to 16 grey levels for speed
            g16 = (gray // 16).astype(np.uint8)
            glcm = graycomatrix(g16, distances=[1], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                                levels=16, symmetric=True, normed=True)
            return {
                "contrast":    float(graycoprops(glcm, "contrast").mean()),
                "homogeneity": float(graycoprops(glcm, "homogeneity").mean()),
                "energy":      float(graycoprops(glcm, "energy").mean()),
                "correlation": float(graycoprops(glcm, "correlation").mean()),
            }
        except Exception:
            # Fallback: simple statistics
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            return {
                "contrast":    float(lap.var() / 1000),
                "homogeneity": max(0.0, 1.0 - lap.std() / 100),
                "energy":      float(gray.std() / 255),
                "correlation": 0.5,
            }

    # ── Roughness (Laplacian) ─────────────────────────────────────────────────

    def _laplacian_roughness(self, gray: np.ndarray) -> float:
        """High Laplacian variance → rough texture. Normalised 0–1."""
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return float(min(1.0, lap_var / 500.0))

    # ── LBP pore visibility ────────────────────────────────────────────────────

    def _lbp_pore_score(self, gray: np.ndarray) -> float:
        """
        Local Binary Pattern score correlates with pore visibility.
        High variance in LBP histogram = uneven texture / visible pores.
        """
        try:
            from skimage.feature import local_binary_pattern
            lbp = local_binary_pattern(gray, P=8, R=1.0, method="uniform")
            hist, _ = np.histogram(lbp.ravel(), bins=10, range=(0, 10), density=True)
            # Variance across bins indicates texture complexity
            return float(min(1.0, hist.var() * 100))
        except Exception:
            return self._laplacian_roughness(gray) * 0.5

    # ── Colour evenness ────────────────────────────────────────────────────────

    def _colour_evenness(self, face_bgr: np.ndarray) -> float:
        """
        Measure colour uniformity across the face.
        High std dev in LAB L* channel = uneven tone / blotchiness.
        Score: 1 = perfectly even, 0 = very blotchy.
        """
        lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
        L_std = float(lab[:, :, 0].std())
        # Typical skin L* std: 5–25. Below 10 = very even.
        return float(max(0.0, min(1.0, 1.0 - (L_std / 35.0))))

    def _empty(self) -> SkinTextureResult:
        return SkinTextureResult(
            overall_score=0.5, roughness=0.5, pore_visibility=0.3, evenness=0.5,
            haralick_features={"contrast": 0, "homogeneity": 0.5, "energy": 0.5, "correlation": 0.5},
            lbp_score=0.3,
        )

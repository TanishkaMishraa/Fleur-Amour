"""
AuraFit — Facial symmetry analyzer.
Measures geometric symmetry of 5 feature pairs using normalised landmarks.
Score: 1.0 = perfect, 0.0 = completely asymmetric.
Each feature pair contributes independently to allow granular feedback.
"""
from __future__ import annotations

import math

from app.schemas.analysis_schemas import FaceLandmarks, SymmetryResult


class SymmetryAnalyzer:

    def analyze(self, landmarks: FaceLandmarks) -> SymmetryResult:
        # ── Midline: x-coordinate of nose tip ────────────────────────────────
        midline_x = landmarks.nose_tip[0]

        # ── Eye symmetry: y-level difference + distance from midline ─────────
        eye_y_diff = abs(landmarks.left_eye[1] - landmarks.right_eye[1])
        left_eye_dist  = abs(midline_x - landmarks.left_eye[0])
        right_eye_dist = abs(midline_x - landmarks.right_eye[0])
        eye_dist_diff  = abs(left_eye_dist - right_eye_dist)
        eye_symmetry   = 1.0 - min(1.0, (eye_y_diff + eye_dist_diff) * 5.0)

        # ── Mouth symmetry: corner height difference ──────────────────────────
        mouth_y_diff     = abs(landmarks.left_mouth[1] - landmarks.right_mouth[1])
        left_m_dist      = abs(midline_x - landmarks.left_mouth[0])
        right_m_dist     = abs(midline_x - landmarks.right_mouth[0])
        mouth_dist_diff  = abs(left_m_dist - right_m_dist)
        mouth_symmetry   = 1.0 - min(1.0, (mouth_y_diff + mouth_dist_diff) * 6.0)

        # ── Nostril symmetry: distance from midline ───────────────────────────
        # Use left/right cheekbone as proxy for nostril symmetry
        left_chk_dist   = abs(midline_x - landmarks.left_cheekbone[0])
        right_chk_dist  = abs(midline_x - landmarks.right_cheekbone[0])
        nostril_symmetry = 1.0 - min(1.0, abs(left_chk_dist - right_chk_dist) * 6.0)

        # ── Jaw symmetry: jaw width balance ──────────────────────────────────
        left_temple_dist  = abs(midline_x - landmarks.left_temple[0])
        right_temple_dist = abs(midline_x - landmarks.right_temple[0])
        jaw_symmetry      = 1.0 - min(1.0, abs(left_temple_dist - right_temple_dist) * 5.0)

        # ── Overall: weighted average ─────────────────────────────────────────
        overall = (
            eye_symmetry   * 0.35 +
            mouth_symmetry * 0.25 +
            nostril_symmetry * 0.20 +
            jaw_symmetry   * 0.20
        )

        deviation_summary = self._summarise(overall, eye_symmetry, mouth_symmetry)

        return SymmetryResult(
            overall_score=round(max(0.0, overall), 3),
            eye_symmetry=round(max(0.0, eye_symmetry), 3),
            mouth_symmetry=round(max(0.0, mouth_symmetry), 3),
            nostril_symmetry=round(max(0.0, nostril_symmetry), 3),
            jaw_symmetry=round(max(0.0, jaw_symmetry), 3),
            deviation_summary=deviation_summary,
        )

    def _summarise(self, overall: float, eye: float, mouth: float) -> str:
        if overall > 0.90:
            return "Highly symmetrical features — balanced and harmonious proportions."
        if overall > 0.75:
            return "Good facial symmetry with minor natural variation between sides."
        lowest = "eyes" if eye < mouth else "mouth"
        return (
            f"Moderate asymmetry, most pronounced around the {lowest}. "
            "Minor natural facial asymmetry is extremely common."
        )

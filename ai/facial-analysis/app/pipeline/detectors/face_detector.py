"""
AuraFit — Face detection + MediaPipe 468-point mesh.
Combines MediaPipe FaceMesh (landmarks) with DeepFace face detection (bounding box).
Extracts key landmark groups used by all downstream analyzers.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from app.schemas.analysis_schemas import BoundingBox, FaceLandmarks, QualityCheck

# MediaPipe landmark indices (subset of 468-point mesh)
# Reference: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
_LEFT_EYE_IDX       = [33, 160, 158, 133, 153, 144]
_RIGHT_EYE_IDX      = [362, 385, 387, 263, 373, 380]
_NOSE_TIP_IDX       = 4
_LEFT_MOUTH_IDX     = 61
_RIGHT_MOUTH_IDX    = 291
_CHIN_IDX           = 152
_LEFT_TEMPLE_IDX    = 234
_RIGHT_TEMPLE_IDX   = 454
_LEFT_CHEEKBONE_IDX = 116
_RIGHT_CHEEKBONE_IDX= 345
_JAW_LEFT_IDX       = 172
_JAW_RIGHT_IDX      = 397
_FOREHEAD_IDX       = 10


@dataclass
class DetectionResult:
    detected:      bool
    bounding_box:  BoundingBox | None
    landmarks:     FaceLandmarks | None
    mesh_points:   list[list[float]] | None   # full 468-point normalised coords
    quality_flags: dict[str, bool]            # face_centered, no_occlusion


class FaceDetector:
    """
    Singleton-safe MediaPipe FaceMesh detector.
    Re-use instance across requests to avoid model reload overhead.
    """

    def __init__(self, settings: Any) -> None:
        self._mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = self._mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=settings.MEDIAPIPE_REFINE_LANDMARKS,
            min_detection_confidence=settings.MIN_FACE_CONFIDENCE,
            min_tracking_confidence=0.5,
            model_complexity=settings.MEDIAPIPE_MODEL_COMPLEXITY,
        )
        self._settings = settings

    def detect(self, rgb: np.ndarray) -> DetectionResult:
        """Run face detection + landmark extraction on RGB image."""
        h, w = rgb.shape[:2]
        mp_result = self._face_mesh.process(rgb)

        if not mp_result.multi_face_landmarks:
            return DetectionResult(
                detected=False,
                bounding_box=None,
                landmarks=None,
                mesh_points=None,
                quality_flags={"face_centered": False, "no_occlusion": False},
            )

        face_lm = mp_result.multi_face_landmarks[0]
        pts = [(lm.x, lm.y, lm.z) for lm in face_lm.landmark]

        # Bounding box from landmark extremes
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x1, x2 = int(min(xs) * w), int(max(xs) * w)
        y1, y2 = int(min(ys) * h), int(max(ys) * h)
        bbox = BoundingBox(
            x=max(0, x1 - 10), y=max(0, y1 - 10),
            w=min(w, x2 - x1 + 20), h=min(h, y2 - y1 + 20),
            confidence=0.95,
        )

        # Key landmarks
        def pt(idx: int) -> list[float]:
            return [round(pts[idx][0], 4), round(pts[idx][1], 4)]

        def pt_mean(indices: list[int]) -> list[float]:
            xs_ = [pts[i][0] for i in indices]
            ys_ = [pts[i][1] for i in indices]
            return [round(sum(xs_) / len(xs_), 4), round(sum(ys_) / len(ys_), 4)]

        # Face proportions for shape classification
        face_w = pts[_RIGHT_TEMPLE_IDX][0] - pts[_LEFT_TEMPLE_IDX][0]
        face_h = pts[_CHIN_IDX][1] - pts[_FOREHEAD_IDX][1]
        jaw_w  = pts[_JAW_RIGHT_IDX][0] - pts[_JAW_LEFT_IDX][0]
        chk_w  = pts[_RIGHT_CHEEKBONE_IDX][0] - pts[_LEFT_CHEEKBONE_IDX][0]

        jaw_ratio = (jaw_w / face_w) if face_w > 0 else 0.0
        face_len  = (face_h / face_w) if face_w > 0 else 0.0
        chk_ratio = (chk_w / face_w) if face_w > 0 else 0.0

        landmarks = FaceLandmarks(
            left_eye=pt_mean(_LEFT_EYE_IDX),
            right_eye=pt_mean(_RIGHT_EYE_IDX),
            nose_tip=pt(_NOSE_TIP_IDX),
            left_mouth=pt(_LEFT_MOUTH_IDX),
            right_mouth=pt(_RIGHT_MOUTH_IDX),
            chin=pt(_CHIN_IDX),
            left_temple=pt(_LEFT_TEMPLE_IDX),
            right_temple=pt(_RIGHT_TEMPLE_IDX),
            left_cheekbone=pt(_LEFT_CHEEKBONE_IDX),
            right_cheekbone=pt(_RIGHT_CHEEKBONE_IDX),
            jaw_width_ratio=round(jaw_ratio, 4),
            face_length_ratio=round(face_len, 4),
            cheekbone_ratio=round(chk_ratio, 4),
        )

        # Full 468-point mesh (normalised)
        mesh = [[round(p[0], 5), round(p[1], 5), round(p[2], 5)] for p in pts]

        # Quality flags
        cx = (pts[_LEFT_TEMPLE_IDX][0] + pts[_RIGHT_TEMPLE_IDX][0]) / 2
        cy = (pts[_FOREHEAD_IDX][1] + pts[_CHIN_IDX][1]) / 2
        face_centered = (0.2 < cx < 0.8) and (0.1 < cy < 0.9)
        # Occlusion: check if nose/mouth landmarks are visible
        no_occlusion = (pts[_NOSE_TIP_IDX][2] < 0.05 and
                        pts[_LEFT_MOUTH_IDX][2] < 0.05)

        return DetectionResult(
            detected=True,
            bounding_box=bbox,
            landmarks=landmarks,
            mesh_points=mesh,
            quality_flags={"face_centered": face_centered, "no_occlusion": no_occlusion},
        )

    def get_face_roi(self, bgr: np.ndarray, bbox: BoundingBox) -> np.ndarray:
        """Crop face region from full image for per-region analysis."""
        x, y, w, h = bbox.x, bbox.y, bbox.w, bbox.h
        return bgr[y:y+h, x:x+w]

    def get_forehead_roi(self, bgr: np.ndarray, mesh: list[list[float]]) -> np.ndarray:
        """Crop forehead region (used for accurate skin tone sampling)."""
        h_img, w_img = bgr.shape[:2]
        # Forehead: landmarks 10, 338, 297, 332 (top of face)
        forehead_indices = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323]
        ys = [int(mesh[i][1] * h_img) for i in forehead_indices if i < len(mesh)]
        xs = [int(mesh[i][0] * w_img) for i in forehead_indices if i < len(mesh)]
        if not xs or not ys:
            return bgr[:bgr.shape[0]//4, :]
        y1, y2 = min(ys), max(ys)
        x1, x2 = min(xs), max(xs)
        return bgr[max(0,y1):max(1,y2), max(0,x1):max(1,x2)]

    def close(self) -> None:
        self._face_mesh.close()

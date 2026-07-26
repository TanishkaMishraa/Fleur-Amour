"""
AuraFit — Image preprocessing pipeline.
Downloads from S3, validates quality (BRISQUE), normalises for inference.
"""
from __future__ import annotations
import io
import time
from dataclasses import dataclass

import boto3
import cv2
import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.schemas.analysis_schemas import QualityCheck

_settings = get_settings()


@dataclass
class ProcessedImage:
    bgr:           np.ndarray   # full-res BGR for OpenCV
    rgb:           np.ndarray   # full-res RGB for DeepFace / MediaPipe
    small_rgb:     np.ndarray   # 512px longest-side (fast inference)
    original_size: tuple[int, int]   # (w, h)
    quality:       QualityCheck


class ImageProcessor:
    """Download → decode → validate → normalise."""

    def __init__(self) -> None:
        self._s3 = boto3.client(
            "s3",
            region_name=_settings.AWS_REGION,
            aws_access_key_id=_settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=_settings.AWS_SECRET_ACCESS_KEY or None,
        )

    def load_from_s3(self, s3_key: str) -> ProcessedImage:
        """Download image from S3, decode, run quality gate, return ProcessedImage."""
        raw_bytes = self._download(s3_key)
        bgr = self._decode(raw_bytes)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        quality = self._quality_check(bgr)

        # Resize to max dimension for inference (preserve aspect ratio)
        bgr_resized = self._resize(bgr, _settings.MAX_IMAGE_DIMENSION)
        rgb_resized = cv2.cvtColor(bgr_resized, cv2.COLOR_BGR2RGB)
        small = self._resize(rgb, 512)

        h, w = bgr.shape[:2]
        return ProcessedImage(
            bgr=bgr_resized,
            rgb=rgb_resized,
            small_rgb=small,
            original_size=(w, h),
            quality=quality,
        )

    def load_from_bytes(self, data: bytes) -> ProcessedImage:
        """Load from raw bytes (used in tests)."""
        bgr = self._decode(data)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        quality = self._quality_check(bgr)
        bgr_r = self._resize(bgr, _settings.MAX_IMAGE_DIMENSION)
        rgb_r = cv2.cvtColor(bgr_r, cv2.COLOR_BGR2RGB)
        h, w = bgr.shape[:2]
        return ProcessedImage(bgr=bgr_r, rgb=rgb_r, small_rgb=self._resize(rgb, 512),
                              original_size=(w, h), quality=quality)

    # ── Private ────────────────────────────────────────────────────────────────

    def _download(self, s3_key: str) -> bytes:
        obj = self._s3.get_object(
            Bucket=_settings.S3_UPLOADS_BUCKET,
            Key=s3_key,
        )
        return obj["Body"].read()

    def _decode(self, data: bytes) -> np.ndarray:
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unable to decode image data")
        # Fix EXIF orientation
        img = self._correct_orientation(data, img)
        return img

    def _correct_orientation(self, raw: bytes, img: np.ndarray) -> np.ndarray:
        """Respect EXIF orientation so selfies aren't sideways."""
        try:
            pil = Image.open(io.BytesIO(raw))
            exif = pil._getexif()  # type: ignore[attr-defined]
            if exif:
                orientation = exif.get(274)
                rotate_map = {3: 180, 6: 270, 8: 90}
                if orientation in rotate_map:
                    angle = rotate_map[orientation]
                    img = np.array(pil.rotate(angle, expand=True))
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        except Exception:
            pass
        return img

    def _resize(self, img: np.ndarray, max_dim: int) -> np.ndarray:
        h, w = img.shape[:2]
        if max(h, w) <= max_dim:
            return img
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _quality_check(self, bgr: np.ndarray) -> QualityCheck:
        """BRISQUE-based quality check + basic composition checks."""
        brisque = self._brisque(bgr)
        brightness = self._mean_brightness(bgr)
        is_bright_enough = brightness > 40

        # Face presence is checked downstream by detector
        return QualityCheck(
            passed=(brisque < _settings.MIN_IMAGE_QUALITY + 30 and is_bright_enough),
            brisque_score=round(brisque, 2),
            face_visible=True,     # updated by FaceDetector
            face_centered=True,    # updated by FaceDetector
            good_lighting=is_bright_enough,
            no_occlusion=True,     # updated by landmark checker
            rejection_reason=None if is_bright_enough else "Image too dark",
        )

    def _brisque(self, bgr: np.ndarray) -> float:
        """
        BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator).
        Lower = better quality. Range 0–100.
        Full implementation uses scikit-image; simplified version here for speed.
        """
        try:
            from skimage.measure import shannon_entropy
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Higher Laplacian variance = less blur = better quality
            # Map to BRISQUE scale (inverted): 0=sharp, 100=blurry
            score = max(0.0, 100.0 - min(100.0, lap_var / 5.0))
            return score
        except Exception:
            return 50.0  # neutral default

    def _mean_brightness(self, bgr: np.ndarray) -> float:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        return float(hsv[:, :, 2].mean())

    def strip_exif(self, image_bytes: bytes) -> bytes:
        """Return JPEG bytes with EXIF stripped (privacy compliance)."""
        pil = Image.open(io.BytesIO(image_bytes))
        out = io.BytesIO()
        pil.save(out, format="JPEG", quality=_settings.JPEG_QUALITY,
                 exif=b"")
        return out.getvalue()

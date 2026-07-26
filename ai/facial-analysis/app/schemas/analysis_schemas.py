"""
AuraFit Facial Analysis Service — Complete Pydantic schemas.
All pipeline inputs, intermediate results, and final API responses.
Versioned output schema: AnalysisResult is the canonical contract
with the user-service consumer.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class FaceShape(StrEnum):
    OVAL      = "oval"
    ROUND     = "round"
    SQUARE    = "square"
    HEART     = "heart"
    OBLONG    = "oblong"
    DIAMOND   = "diamond"
    TRIANGLE  = "triangle"
    UNKNOWN   = "unknown"


class SkinTone(StrEnum):
    FAIR   = "fair"
    LIGHT  = "light"
    MEDIUM = "medium"
    OLIVE  = "olive"
    TAN    = "tan"
    DEEP   = "deep"


class Undertone(StrEnum):
    COOL    = "cool"
    WARM    = "warm"
    NEUTRAL = "neutral"


class HairType(StrEnum):
    STRAIGHT = "straight"
    WAVY     = "wavy"
    CURLY    = "curly"
    COILY    = "coily"
    UNKNOWN  = "unknown"


class SkinConcern(StrEnum):
    ACNE            = "acne"
    DARK_CIRCLES    = "dark_circles"
    HYPERPIGMENTATION = "hyperpigmentation"
    FINE_LINES      = "fine_lines"
    PORES           = "enlarged_pores"
    REDNESS         = "redness"
    DRYNESS         = "dryness"
    OILINESS        = "oiliness"
    TEXTURE         = "uneven_texture"
    DARK_SPOTS      = "dark_spots"


# ══════════════════════════════════════════════════════════════════════════════
# PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════

class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int
    confidence: float = Field(ge=0.0, le=1.0)


class FaceLandmarks(BaseModel):
    """Key landmark coordinates (normalised 0–1 relative to image dimensions)."""
    left_eye:         list[float]
    right_eye:        list[float]
    nose_tip:         list[float]
    left_mouth:       list[float]
    right_mouth:      list[float]
    chin:             list[float]
    left_temple:      list[float]
    right_temple:     list[float]
    left_cheekbone:   list[float]
    right_cheekbone:  list[float]
    # Derived proportions (used by shape classifier)
    jaw_width_ratio:    float = Field(description="jaw_width / face_width")
    face_length_ratio:  float = Field(description="face_height / face_width")
    cheekbone_ratio:    float = Field(description="cheekbone_width / face_width")


class QualityCheck(BaseModel):
    passed:            bool
    brisque_score:     float = Field(description="Lower is better. Reject > 70.")
    face_visible:      bool
    face_centered:     bool
    good_lighting:     bool
    no_occlusion:      bool
    rejection_reason:  str | None = None


# ══════════════════════════════════════════════════════════════════════════════
# PER-ANALYZER RESULTS
# ══════════════════════════════════════════════════════════════════════════════

class FaceShapeResult(BaseModel):
    shape:       FaceShape
    confidence:  float = Field(ge=0.0, le=1.0)
    ratios:      dict[str, float]    # jaw_ratio, face_length, cheekbone_ratio
    description: str                  # human-readable explanation


class SkinToneResult(BaseModel):
    tone:        SkinTone
    undertone:   Undertone
    ita_angle:   float    = Field(description="ITA° (Individual Typology Angle)")
    lab_values:  dict[str, float]    # L*, a*, b* mean values from forehead ROI
    hex_color:   str      = Field(description="Closest hex code for UI swatch")
    fitzpatrick: int      = Field(ge=1, le=6, description="Fitzpatrick phototype I–VI")
    confidence:  float    = Field(ge=0.0, le=1.0)


class AgeEstimationResult(BaseModel):
    estimated_age: int    = Field(ge=1, le=100)
    age_range:     str    = Field(description="e.g. '25-34'")
    confidence:    float  = Field(ge=0.0, le=1.0)
    model:         str    = Field(description="DeepFace model used")


class HairAnalysisResult(BaseModel):
    hair_detected: bool
    hair_type:     HairType
    dominant_color: str          # hex
    color_names:   list[str]     # ["dark brown", "auburn"]
    texture_score: float | None  # 0=fine, 1=coarse
    shine_score:   float | None  # 0=matte, 1=shiny
    volume_score:  float | None  # 0=flat, 1=voluminous


class SkinConcernResult(BaseModel):
    concern:     SkinConcern
    severity:    float = Field(ge=0.0, le=1.0, description="0=none, 1=severe")
    region:      str   = Field(description="forehead|cheeks|nose|chin|under_eyes")
    pixel_count: int | None = None


class AcneAnalysisResult(BaseModel):
    detected:     bool
    count:        int
    severity:     str                   # none|mild|moderate|severe
    severity_score: float = Field(ge=0.0, le=1.0)
    regions:      list[str]            # ["forehead", "cheeks"]
    concerns:     list[SkinConcernResult]


class DarkCircleResult(BaseModel):
    detected:     bool
    severity:     float = Field(ge=0.0, le=1.0)
    lab_delta:    float = Field(description="ΔL* between under-eye and cheek skin")
    category:     str   = Field(description="none|mild|moderate|severe")
    vascularity:  bool  = Field(description="True if blue/purple hue (vascular)")


class SkinTextureResult(BaseModel):
    overall_score:    float = Field(ge=0.0, le=1.0, description="1=smooth, 0=rough")
    roughness:        float
    pore_visibility:  float
    evenness:         float
    haralick_features: dict[str, float]   # contrast, homogeneity, energy, correlation
    lbp_score:        float | None        # Local Binary Pattern texture score


class SymmetryResult(BaseModel):
    overall_score:     float = Field(ge=0.0, le=1.0, description="1=perfect symmetry")
    eye_symmetry:      float
    mouth_symmetry:    float
    nostril_symmetry:  float
    jaw_symmetry:      float
    deviation_summary: str                # human-readable


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE I/O
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    """Payload from user-service Celery task."""
    s3_key:   str  = Field(..., description="S3 key in uploads bucket")
    user_id:  str
    task_id:  str


class ProgressUpdate(BaseModel):
    task_id:  str
    step:     str
    progress: int = Field(ge=0, le=100)


class AnalysisResult(BaseModel):
    """
    Complete facial analysis result — the canonical contract
    returned to user-service and stored in facial_scans.skin_analysis.
    """
    # Pipeline metadata
    pipeline_version: str
    processing_time_ms: float
    quality: QualityCheck

    # Geometry
    face_shape:         FaceShapeResult
    landmarks:          FaceLandmarks
    mesh_points:        list[list[float]]   # 468-point normalised mesh
    bounding_box:       BoundingBox
    symmetry:           SymmetryResult

    # Skin
    skin_tone:          SkinToneResult
    age_estimation:     AgeEstimationResult
    acne_analysis:      AcneAnalysisResult
    dark_circles:       DarkCircleResult
    skin_texture:       SkinTextureResult
    skin_concerns:      list[SkinConcernResult]

    # Hair
    hair_analysis:      HairAnalysisResult

    # Beauty recommendations derived from results
    makeup_recommendations:  dict[str, Any]
    skincare_recommendations: dict[str, Any]
    hairstyle_recommendations: list[str]


class AnalysisErrorResponse(BaseModel):
    task_id:      str
    error_code:   str
    error_message:str
    retryable:    bool = True


# ── API request/response wrappers ──────────────────────────────────────────────

class SyncAnalyzeResponse(BaseModel):
    """For /analyze endpoint (sync, low-latency path)."""
    success:   bool
    task_id:   str
    result:    AnalysisResult | None = None
    error:     AnalysisErrorResponse | None = None


class HealthResponse(BaseModel):
    status:          str
    service:         str
    version:         str
    gpu_available:   bool
    model_loaded:    bool
    uptime_seconds:  float

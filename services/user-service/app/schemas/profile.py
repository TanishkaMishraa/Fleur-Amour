"""
AuraFit — Profile request/response schemas.
Covers UserProfile (beauty/style) and FragranceProfile.
All list fields use Python list[str] — serialised as JSONB in DB.
"""
from __future__ import annotations

from pydantic import Field, field_validator

from app.schemas.base import AuraFitSchema, TimestampSchema, UUIDSchema


# ── Profile enums (mirrors ORM enums, kept here for Pydantic validation) ─────

class SkinTone(str):
    pass

VALID_SKIN_TONES = {"fair", "light", "medium", "olive", "tan", "deep"}
VALID_SKIN_TYPES = {"normal", "dry", "oily", "combination", "sensitive"}
VALID_UNDERTONES = {"cool", "warm", "neutral"}
VALID_BODY_SHAPES = {"hourglass", "pear", "apple", "rectangle", "inverted_triangle"}


# ── Request schemas ───────────────────────────────────────────────────────────

class ProfileUpsertRequest(AuraFitSchema):
    """
    Full or partial profile update.
    All fields optional — allows incremental onboarding.
    """
    # Physical attributes
    skin_tone: str | None = Field(None, description=f"One of: {VALID_SKIN_TONES}")
    skin_type: str | None = Field(None, description=f"One of: {VALID_SKIN_TYPES}")
    undertone: str | None = Field(None, description=f"One of: {VALID_UNDERTONES}")
    hair_type: str | None = Field(None, max_length=50)
    hair_color: str | None = Field(None, max_length=50)
    eye_color: str | None = Field(None, max_length=50)
    body_shape: str | None = Field(None, description=f"One of: {VALID_BODY_SHAPES}")
    height_cm: float | None = Field(None, gt=0, lt=300)
    weight_kg: float | None = Field(None, gt=0, lt=500)
    age_range: str | None = Field(None, max_length=20, examples=["18-24", "25-34"])

    # Style & fragrance preferences
    style_archetypes: list[str] | None = Field(
        None, max_length=10,
        examples=[["minimalist", "boho"]],
    )
    fragrance_family: list[str] | None = Field(
        None, max_length=10,
        examples=[["woody", "floral"]],
    )
    skin_concerns: list[str] | None = Field(
        None, max_length=15,
        examples=[["acne", "hyperpigmentation"]],
    )
    avoided_ingredients: list[str] | None = Field(
        None, max_length=30,
    )

    # Budget & locale
    budget_range: str | None = Field(
        None, max_length=20, examples=["budget", "mid-range", "luxury"]
    )
    currency: str | None = Field(None, min_length=3, max_length=3)

    @field_validator("skin_tone")
    @classmethod
    def validate_skin_tone(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SKIN_TONES:
            raise ValueError(f"skin_tone must be one of {VALID_SKIN_TONES}")
        return v

    @field_validator("skin_type")
    @classmethod
    def validate_skin_type(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SKIN_TYPES:
            raise ValueError(f"skin_type must be one of {VALID_SKIN_TYPES}")
        return v

    @field_validator("undertone")
    @classmethod
    def validate_undertone(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_UNDERTONES:
            raise ValueError(f"undertone must be one of {VALID_UNDERTONES}")
        return v

    @field_validator("body_shape")
    @classmethod
    def validate_body_shape(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_BODY_SHAPES:
            raise ValueError(f"body_shape must be one of {VALID_BODY_SHAPES}")
        return v


# ── Response schemas ──────────────────────────────────────────────────────────

class ProfileOut(UUIDSchema, TimestampSchema):
    """Full beauty/style profile response."""
    user_id: str
    skin_tone: str | None
    skin_type: str | None
    undertone: str | None
    hair_type: str | None
    hair_color: str | None
    eye_color: str | None
    body_shape: str | None
    height_cm: float | None
    weight_kg: float | None
    age_range: str | None
    style_archetypes: list | None
    fragrance_family: list | None
    skin_concerns: list | None
    avoided_ingredients: list | None
    budget_range: str | None
    currency: str
    onboarding_complete: bool
    quiz_version: int


# ── Fragrance schemas ─────────────────────────────────────────────────────────

class FragranceProfileRequest(AuraFitSchema):
    preferred_notes: list[str] | None = Field(
        None, max_length=20, examples=[["rose", "oud", "vanilla"]]
    )
    avoided_notes: list[str] | None = Field(None, max_length=20)
    previous_fragrances: list[dict] | None = Field(
        None, max_length=50,
        examples=[[{"name": "Chanel No.5", "rating": 5}]],
    )
    intensity_preference: str | None = Field(
        None, examples=["light", "moderate", "strong"]
    )
    longevity_preference: str | None = Field(
        None, examples=["fresh", "all_day", "long_lasting"]
    )


class FragranceProfileOut(UUIDSchema, TimestampSchema):
    user_profile_id: str
    preferred_notes: list | None
    avoided_notes: list | None
    previous_fragrances: list | None
    intensity_preference: str | None
    longevity_preference: str | None

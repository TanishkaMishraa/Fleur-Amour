"""
AuraFit — User preferences schemas (Stage 3).
Read + update preferences. All fields optional on update (PATCH semantics).
"""
from __future__ import annotations

from typing import Literal
from pydantic import field_validator
from app.schemas.base import AuraFitSchema


class PreferencesOut(AuraFitSchema):
    # Notifications
    email_marketing:        bool
    email_recommendations:  bool
    email_product_updates:  bool
    email_security_alerts:  bool
    push_recommendations:   bool
    push_tryon_complete:    bool
    push_scan_complete:     bool
    in_app_notifications:   bool
    # Display
    theme:            str
    language:         str
    currency:         str
    measurement_unit: str
    # Privacy
    profile_public:        bool
    allow_data_training:   bool
    allow_personalisation: bool


class PreferencesUpdateRequest(AuraFitSchema):
    """PATCH — all fields optional. Only provided fields are updated."""
    email_marketing:        bool | None = None
    email_recommendations:  bool | None = None
    email_product_updates:  bool | None = None
    email_security_alerts:  bool | None = None
    push_recommendations:   bool | None = None
    push_tryon_complete:    bool | None = None
    push_scan_complete:     bool | None = None
    in_app_notifications:   bool | None = None
    theme:            Literal["dark", "light", "system"] | None = None
    language:         str | None = None
    currency:         str | None = None
    measurement_unit: Literal["metric", "imperial"] | None = None
    profile_public:        bool | None = None
    allow_data_training:   bool | None = None
    allow_personalisation: bool | None = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) != 3 or not v.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code (e.g. USD)")
        return v.upper()

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        allowed = {"en", "fr", "es", "de", "it", "pt", "ja", "ko", "zh", "ar", "hi"}
        if v and v.lower() not in allowed:
            raise ValueError(f"Language must be one of: {', '.join(sorted(allowed))}")
        return v.lower() if v else v

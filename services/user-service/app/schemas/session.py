"""
AuraFit — Session schemas (Stage 3).
Session list, revoke, and session detail for security page.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.base import AuraFitSchema


class SessionOut(AuraFitSchema):
    id:             uuid.UUID
    device_name:    str | None
    device_type:    str | None        # mobile | desktop | tablet
    ip_address:     str | None
    location:       str | None
    last_active_at: datetime | None
    created_at:     datetime
    is_current:     bool = False


class RevokeSessionRequest(AuraFitSchema):
    session_id: uuid.UUID


class SessionListOut(AuraFitSchema):
    sessions: list[SessionOut]
    total:    int

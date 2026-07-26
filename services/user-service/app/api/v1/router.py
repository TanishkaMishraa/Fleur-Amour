"""
AuraFit — API v1 router (Stage 10: Complete Integration).
All sub-routers assembled here. Mounted at /api/v1 in main.py.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    analysis,
    auth,
    chat,
    color,
    health,
    mfa,
    preferences,
    profiles,
    sessions,
    uploads,
    users,
    wardrobes,
)

api_router = APIRouter()

# ── Infrastructure ──────────────────────────────────────────────────────────
api_router.include_router(health.router)

# ── Authentication (public + protected mix) ─────────────────────────────────
api_router.include_router(auth.router)
api_router.include_router(sessions.router)
api_router.include_router(mfa.router)

# ── User management (all protected) ────────────────────────────────────────
api_router.include_router(users.router)
api_router.include_router(profiles.router)
api_router.include_router(preferences.router)

# ── Feature domains ─────────────────────────────────────────────────────────
api_router.include_router(wardrobes.router)
api_router.include_router(analysis.router)
api_router.include_router(uploads.router)
api_router.include_router(chat.router)
api_router.include_router(color.router)

# ── Style DNA ───────────────────────────────────────────────────────────────
try:
    from app.api.v1.endpoints import style_dna
    api_router.include_router(style_dna.router)
except ImportError:
    pass

# ── Subscriptions ───────────────────────────────────────────────────────────
try:
    from app.api.v1.endpoints import subscriptions
    api_router.include_router(subscriptions.router)
except ImportError:
    pass

# ── Admin ───────────────────────────────────────────────────────────────────
try:
    from app.api.v1.endpoints import admin
    api_router.include_router(admin.router)
except ImportError:
    pass


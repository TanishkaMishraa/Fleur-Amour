"""
AuraFit — ORM model registry.
All models imported here so Alembic autogenerate and SQLAlchemy relationship
resolution can discover them regardless of import order.
"""
# Order: Base → independent tables → tables with FKs

from app.db.base import AuraFitBase as Base  # noqa: F401

from app.models.user import User, OAuthAccount  # noqa: F401
from app.models.profile import UserProfile  # noqa: F401
from app.models.analysis import FacialScan, FragranceProfile  # noqa: F401
from app.models.image import Upload  # noqa: F401
from app.models.recommendation import (  # noqa: F401
    RecommendationSession,
    Recommendation,
    UserProductInteraction,
    SavedProduct,
)
from app.models.wardrobe import Wardrobe, WardrobeItem, Outfit, OutfitItem  # noqa: F401
from app.models.chat import ChatSession, ChatMessage  # noqa: F401
from app.models.report import StyleReport, Notification, NotificationPreferences  # noqa: F401

__all__ = [
    "Base",
    "User", "OAuthAccount",
    "UserProfile",
    "FacialScan", "FragranceProfile",
    "Upload",
    "RecommendationSession", "Recommendation",
    "UserProductInteraction", "SavedProduct",
    "Wardrobe", "WardrobeItem", "Outfit", "OutfitItem",
    "ChatSession", "ChatMessage",
    "StyleReport", "Notification", "NotificationPreferences",
]

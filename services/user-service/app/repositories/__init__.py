"""
AuraFit — Repository package.
All repository classes re-exported from here for clean imports.
"""
from app.repositories.base import BaseRepository
from app.repositories.user_repository import UserRepository, OAuthAccountRepository
from app.repositories.profile_repository import (
    UserProfileRepository,
    FacialScanRepository,
    FragranceProfileRepository,
)
from app.repositories.wardrobe_repository import (
    WardrobeRepository,
    WardrobeItemRepository,
    OutfitRepository,
)
from app.repositories.chat_repository import ChatSessionRepository, ChatMessageRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "OAuthAccountRepository",
    "UserProfileRepository",
    "FacialScanRepository",
    "FragranceProfileRepository",
    "WardrobeRepository",
    "WardrobeItemRepository",
    "OutfitRepository",
    "ChatSessionRepository",
    "ChatMessageRepository",
]

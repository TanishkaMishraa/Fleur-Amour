"""
AuraFit — Analysis repository compatibility module.
FacialScanRepository and FragranceProfileRepository live in profile_repository.py.
This module re-exports them so any code that imports from analysis_repository still works.
"""
from app.repositories.profile_repository import (  # noqa: F401
    FacialScanRepository,
    FragranceProfileRepository,
)

__all__ = ["FacialScanRepository", "FragranceProfileRepository"]

"""
AuraFit — app/tasks/celery_app.py
Re-exports the canonical celery_app from integrations.
Tasks import from here; avoids circular imports with integrations/.
"""
from app.integrations.celery_app import celery_app  # noqa: F401

__all__ = ["celery_app"]

"""
AuraFit — Celery application factory (integrations/celery_app.py).
Canonical factory. app/tasks/celery_app.py re-exports from here.
Stage 0 queue topology: default, ai.high, ai.low,
recommendations, notifications, media, maintenance.
Celery Beat periodic schedule defined here.
"""
from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import get_settings


def _get_settings():
    return get_settings()


def create_celery_app() -> Celery:
    settings = _get_settings()

    celery = Celery("aurafit")
    celery.config_from_object({
        # ── Broker & backend ─────────────────────────────────────────────────
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,

        # ── Serialisation ────────────────────────────────────────────────────
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "result_expires": 86400,  # 24h

        # ── Timezone ─────────────────────────────────────────────────────────
        "timezone": "UTC",
        "enable_utc": True,

        # ── Queues (Stage 0 topology) ─────────────────────────────────────────
        "task_queues": [
            Queue("default",         Exchange("default"),         routing_key="default"),
            Queue("ai.high",         Exchange("ai"),              routing_key="ai.high"),
            Queue("ai.low",          Exchange("ai"),              routing_key="ai.low"),
            Queue("recommendations", Exchange("recommendations"), routing_key="recommendations"),
            Queue("notifications",   Exchange("notifications"),   routing_key="notifications"),
            Queue("media",           Exchange("media"),           routing_key="media"),
            Queue("maintenance",     Exchange("maintenance"),     routing_key="maintenance"),
        ],
        "task_default_queue": "default",
        "task_default_exchange": "default",
        "task_default_routing_key": "default",

        # ── Task routing ─────────────────────────────────────────────────────
        "task_routes": {
            "app.tasks.ai_tasks.run_facial_scan":        {"queue": "ai.high"},
            "app.tasks.ai_tasks.run_tryon":              {"queue": "media"},
            "app.tasks.ai_tasks.run_skin_analysis":      {"queue": "ai.high"},
            "app.tasks.ai_tasks.run_outfit_generation":  {"queue": "ai.low"},
            "app.tasks.rec_tasks.refresh_user_recommendations": {"queue": "recommendations"},
            "app.tasks.rec_tasks.rebuild_cf_model":             {"queue": "ai.low"},
            "app.tasks.rec_tasks.refresh_product_embeddings":   {"queue": "ai.low"},
            "app.tasks.notification_tasks.send_verification_email_task": {"queue": "notifications"},
            "app.tasks.notification_tasks.send_password_reset_task":     {"queue": "notifications"},
            "app.tasks.notification_tasks.send_push_task":               {"queue": "notifications"},
            "app.tasks.maintenance_tasks.purge_expired_sessions":        {"queue": "maintenance"},
            "app.tasks.maintenance_tasks.aggregate_analytics":           {"queue": "maintenance"},
            "app.tasks.maintenance_tasks.schedule_account_deletion":     {"queue": "maintenance"},
        },

        # ── Reliability ───────────────────────────────────────────────────────
        "task_acks_late": True,              # ack AFTER task completes
        "task_reject_on_worker_lost": True,
        "worker_prefetch_multiplier": 1,     # prevent queue hoarding

        # ── Retry defaults (tasks override individually) ────────────────────
        "task_max_retries": 3,
        "task_default_retry_delay": 10,

        # ── Monitoring ────────────────────────────────────────────────────────
        "worker_send_task_events": True,
        "task_send_sent_event": True,
        "task_track_started": True,

        # ── Test mode ─────────────────────────────────────────────────────────
        "task_always_eager": settings.CELERY_TASK_ALWAYS_EAGER,
        "task_eager_propagates": True,

        # ── Celery Beat periodic schedule ────────────────────────────────────
        "beat_schedule": {
            "purge-expired-sessions": {
                "task": "app.tasks.maintenance_tasks.purge_expired_sessions",
                "schedule": 3600.0,       # hourly
                "options": {"queue": "maintenance"},
            },
            "aggregate-analytics": {
                "task": "app.tasks.maintenance_tasks.aggregate_analytics",
                "schedule": 86400.0,      # daily
                "options": {"queue": "maintenance"},
            },
            "rebuild-cf-model": {
                "task": "app.tasks.rec_tasks.rebuild_cf_model",
                "schedule": 86400.0,      # nightly
                "options": {"queue": "ai.low"},
            },
            "refresh-product-embeddings": {
                "task": "app.tasks.rec_tasks.refresh_product_embeddings",
                "schedule": 43200.0,      # twice daily
                "options": {"queue": "ai.low"},
            },
        },

        # ── Auto-discover ─────────────────────────────────────────────────────
        "include": [
            "app.tasks.ai_tasks",
            "app.tasks.notification_tasks",
            "app.tasks.rec_tasks",
            "app.tasks.maintenance_tasks",
        ],
    })

    return celery


celery_app = create_celery_app()

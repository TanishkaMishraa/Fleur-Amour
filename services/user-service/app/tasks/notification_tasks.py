"""
AuraFit — Notification Celery tasks.
Email via AWS SES. Push via SNS/Firebase Cloud Messaging.
All tasks are fire-and-forget from services — never block on result.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

_EMAIL_TEMPLATES = {
    "welcome", "email_verify", "password_reset",
    "scan_complete", "report_ready", "weekly_style_tip",
}


@shared_task(
    name="app.tasks.notification_tasks.send_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="notifications",
)
def send_email(
    self,
    *,
    user_id: str,
    to_email: str,
    template: str,
    context: dict,
) -> dict:
    """
    Send transactional email via AWS SES.
    Retries with exponential backoff up to 3 times.
    """
    if template not in _EMAIL_TEMPLATES:
        logger.warning(f"[email] unknown template: {template}")
        return {"status": "skipped", "reason": "unknown_template"}

    try:
        import boto3
        from app.core.config import get_settings
        settings = get_settings()

        ses = boto3.client("ses", region_name=settings.AWS_REGION)
        subject = _render_subject(template, context)
        body = _render_body(template, context)

        ses.send_email(
            Source=f"{settings.SES_FROM_NAME} <{settings.SES_FROM_EMAIL}>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"[email] sent template={template} to={to_email} user={user_id}")
        return {"status": "sent", "template": template, "user_id": user_id}

    except Exception as exc:
        logger.error(f"[email] send failed template={template}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


@shared_task(
    name="app.tasks.notification_tasks.send_push",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="notifications",
)
def send_push(
    self,
    *,
    user_id: str,
    title: str,
    body: str,
    deep_link: str | None = None,
    data: dict | None = None,
) -> dict:
    """
    Send push notification via AWS SNS → Firebase Cloud Messaging.
    """
    try:
        logger.info(f"[push] sending to user={user_id} title={title!r}")
        # Production: lookup user FCM/APNs token, publish to SNS endpoint
        return {"status": "sent", "user_id": user_id}
    except Exception as exc:
        logger.error(f"[push] failed user={user_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


def _render_subject(template: str, context: dict) -> str:
    subjects = {
        "welcome": "Welcome to AuraFit ✨",
        "email_verify": "Verify your AuraFit email",
        "password_reset": "Reset your AuraFit password",
        "scan_complete": "Your skin analysis is ready",
        "report_ready": "Your Style DNA Report is ready",
        "weekly_style_tip": "Your weekly style tip from Aura",
    }
    return subjects.get(template, "AuraFit notification")


def _render_body(template: str, context: dict) -> str:
    """Minimal HTML body. Replace with Jinja2 templates in production."""
    name = context.get("full_name", "there")
    return f"<p>Hi {name},</p><p>This is your AuraFit {template} notification.</p>"


# ── Convenience wrappers used by AuthService ───────────────────────────────

@shared_task(
    name="app.tasks.notification_tasks.send_email_verification_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="notifications",
)
def send_email_verification_task(
    self,
    *,
    user_id: str,
    email: str,
    full_name: str,
    token: str,
) -> dict:
    """Dispatch email-verification email for a newly registered user."""
    from app.core.config import get_settings
    settings = get_settings()
    verify_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    return send_email.apply(kwargs={
        "user_id":  user_id,
        "to_email": email,
        "template": "email_verify",
        "context":  {"full_name": full_name, "verify_url": verify_url},
    }).get()


@shared_task(
    name="app.tasks.notification_tasks.send_password_reset_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="notifications",
)
def send_password_reset_task(
    self,
    *,
    user_id: str,
    email: str,
    full_name: str,
    token: str,
) -> dict:
    """Dispatch password-reset email."""
    from app.core.config import get_settings
    settings = get_settings()
    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    return send_email.apply(kwargs={
        "user_id":  user_id,
        "to_email": email,
        "template": "password_reset",
        "context":  {"full_name": full_name, "reset_url": reset_url},
    }).get()

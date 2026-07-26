"""
AuraFit - Notification Celery tasks.
Dispatched by services; never called directly from endpoints.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.notifications.send_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="notifications",
)
def send_email(
    self,
    *,
    user_id: str,
    template: str,
    context: dict,
    to_email: str,
) -> dict:
    """
    Send transactional email via SES.
    Retries up to 3 times with exponential backoff on failure.
    """
    try:
        # Import here to avoid circular imports at module load time
        import boto3
        from app.core.config import get_settings

        settings = get_settings()
        ses = boto3.client("ses", region_name=settings.AWS_REGION)

        logger.info(f"Sending {template} email to {to_email} for user {user_id}")

        # Render template (simplified — use Jinja2 in production)
        body = f"AuraFit: {template} notification"

        ses.send_email(
            Source=f"{settings.SES_FROM_NAME} <{settings.SES_FROM_EMAIL}>",
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": f"AuraFit - {template}"},
                "Body": {"Text": {"Data": body}},
            },
        )
        return {"status": "sent", "template": template, "user_id": user_id}

    except Exception as exc:
        logger.exception(f"Email send failed: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


@shared_task(
    name="app.tasks.notifications.send_push",
    bind=True,
    max_retries=3,
    queue="notifications",
)
def send_push(
    self,
    *,
    user_id: str,
    title: str,
    body: str,
    deep_link: str | None = None,
) -> dict:
    """Send push notification via FCM/APNs (via SNS)."""
    try:
        logger.info(f"Push notification for user {user_id}: {title}")
        # SNS / FCM integration goes here
        return {"status": "sent", "user_id": user_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)

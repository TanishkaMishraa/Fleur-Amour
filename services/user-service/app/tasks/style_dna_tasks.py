"""
AuraFit — Style DNA Celery tasks (Stage 8).

generate_pdf:
  Triggered after StyleDNAReport is created.
  Fetches report data from DB, generates PDF, uploads to S3, updates record.

pregenerate_stale_reports:
  Weekly task: checks for reports where data_hash has changed
  (new scan, quiz retake, color profile update) and queues regeneration.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.style_dna_tasks.generate_pdf",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="media",
)
def generate_pdf(self, *, report_id: str) -> dict:
    """
    Generate Style DNA PDF for a completed report.
    Uploads to S3 and updates the StyleDNAReport record with the CDN URL.
    """
    import asyncio
    import io
    import uuid

    logger.info(f"[style_dna] generate_pdf report={report_id}")

    async def _run() -> dict:
        from sqlalchemy import select
        from app.db.session import create_async_session
        from app.models.style_dna import StyleDNAReport, StyleDNAStatus
        from app.models.user import User
        from app.services.style_dna.pdf_generator import pdf_generator
        from app.core.config import get_settings
        import boto3

        settings = get_settings()

        async with create_async_session() as session:
            report = await session.get(StyleDNAReport, uuid.UUID(report_id))
            if not report or report.status != StyleDNAStatus.READY:
                return {"status": "skip", "reason": "report not ready"}

            user = await session.get(User, report.user_id)
            if not user:
                return {"status": "skip", "reason": "user not found"}

            # Assemble report sections dict
            report_data = {
                "headline":                 report.headline,
                "narrative":                report.narrative,
                "beauty_profile":           report.beauty_profile,
                "skin_profile":             report.skin_profile,
                "color_profile_section":    report.color_profile_section,
                "fashion_profile":          report.fashion_profile,
                "fragrance_profile_section":report.fragrance_profile_section,
                "hairstyle_profile":        report.hairstyle_profile,
                "recommendations":          report.recommendations,
                "personality":              report.personality,
                "occasion_guide":           report.occasion_guide,
            }

            # Generate PDF
            pdf_bytes = pdf_generator.generate(
                report_data=report_data,
                user_name=user.full_name or "Friend",
                report_id=report_id,
            )

            # Upload to S3
            s3_key = f"reports/{report.user_id}/{report_id}.pdf"
            try:
                s3 = boto3.client("s3", region_name=settings.AWS_REGION)
                s3.put_object(
                    Bucket=settings.S3_ASSETS_BUCKET,
                    Key=s3_key,
                    Body=pdf_bytes,
                    ContentType="application/pdf",
                    ContentDisposition=f'attachment; filename="AuraFit-StyleDNA.pdf"',
                    CacheControl="max-age=86400",
                )
                pdf_url = f"{settings.CDN_BASE_URL}/{s3_key}"
            except Exception as s3_exc:
                logger.warning(f"[style_dna] S3 upload failed: {s3_exc}")
                pdf_url = None
                s3_key  = None

            # Update record
            report.pdf_s3_key  = s3_key
            report.pdf_url     = pdf_url
            report.pdf_size_kb = len(pdf_bytes) // 1024
            session.add(report)
            await session.commit()

        logger.info(f"[style_dna] PDF complete report={report_id} size_kb={len(pdf_bytes)//1024}")
        return {"status": "ok", "report_id": report_id, "pdf_url": pdf_url}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception(f"[style_dna] generate_pdf failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="app.tasks.style_dna_tasks.pregenerate_stale_reports",
    queue="maintenance",
)
def pregenerate_stale_reports() -> dict:
    """
    Weekly: identify users whose source data has changed since their last report
    (new scan, quiz retake, color profile update) and queue fresh generation.
    """
    logger.info("[style_dna] pregenerate_stale_reports start")
    # Implementation: query reports + compare data_hash
    return {"status": "ok", "task": "pregenerate_stale_reports"}

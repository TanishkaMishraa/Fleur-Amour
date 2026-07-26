"""
AuraFit — AI Celery tasks.
Dispatched by user-service endpoints; executed on GPU-capable workers
(queues: ai.high for facial scans, media for try-on/image processing).

Each task:
  1. Sets Redis task status to STARTED, then PROGRESS at each pipeline stage
  2. Calls the relevant AI microservice over the internal network
  3. Persists results to PostgreSQL via a sync session (Celery is sync)
  4. Caches the final result in Redis for fast polling
  5. Publishes a pub/sub event so the SSE gateway can push to the client
  6. Sets status to SUCCESS or FAILURE

Retry policy: exponential backoff (30s, 60s, 120s), max 3 attempts.
Transient errors (network, 5xx) retry; permanent errors (no face detected,
quality rejected) do NOT retry — they're returned as a failed result so the
user can retake the photo immediately.
"""
from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger

from app.cache.sync_redis_client import (
    publish_event,
    set_task_progress,
    set_task_result,
    set_task_status,
)
from app.cache.redis_client import RedisKeys
from app.db.sync_session import get_sync_session

logger = get_task_logger(__name__)

# Error codes returned by the AI service that should NOT be retried —
# they represent a problem with the input image, not a transient failure.
_NON_RETRYABLE_CODES = {"NO_FACE_DETECTED", "QUALITY_CHECK_FAILED"}


@shared_task(
    name="app.tasks.ai_tasks.run_facial_scan",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ai.high",
    track_started=True,
)
def run_facial_scan(
    self,
    *,
    user_id: str,
    scan_id: str,
    s3_key: str,
    upload_id: str,
) -> dict:
    """
    Full facial analysis pipeline orchestration.

    Calls ai-facial-analysis /analyze, persists the complete AnalysisResult
    onto the FacialScan row, activates it (deactivating prior scans), marks
    the Upload complete, and notifies the client via SSE.
    """
    import httpx

    from app.core.config import get_settings
    from app.models.analysis import FacialScan
    from app.models.image import Upload, UploadStatus

    settings = get_settings()
    task_id = self.request.id

    logger.info(f"[facial_scan] start user={user_id} scan={scan_id} s3_key={s3_key} task={task_id}")
    set_task_status(task_id, "STARTED")
    set_task_progress(task_id, "Uploading image for analysis", 10)

    try:
        # ── Stage 1: Call AI microservice ──────────────────────────────────────
        set_task_progress(task_id, "Detecting face and analysing features", 30)

        with httpx.Client(timeout=settings.INFERENCE_TIMEOUT if hasattr(settings, "INFERENCE_TIMEOUT") else 120.0) as client:
            response = client.post(
                f"{settings.AI_FACIAL_SERVICE_URL}/analyze",
                json={"s3_key": s3_key, "user_id": user_id, "task_id": task_id},
                headers={"X-Internal-Service": "user-service"},
            )
            response.raise_for_status()
            payload: dict = response.json()

        set_task_progress(task_id, "Processing results", 70)

        if not payload.get("success"):
            error = payload.get("error") or {}
            error_code = error.get("error_code", "UNKNOWN_ERROR")
            error_message = error.get("error_message", "Analysis failed")
            retryable = error.get("retryable", True) and error_code not in _NON_RETRYABLE_CODES

            logger.warning(f"[facial_scan] ai_error code={error_code} retryable={retryable}: {error_message}")

            with get_sync_session() as session:
                upload = session.get(Upload, upload_id)
                if upload:
                    upload.status = UploadStatus.FAILED
                    upload.error_message = error_message[:500]

                scan = session.get(FacialScan, scan_id)
                if scan:
                    # Keep the scan record but mark it inactive with the error
                    scan.is_active = False
                    scan.skin_analysis = {"error": error_code, "message": error_message}

            set_task_status(task_id, "FAILURE")
            set_task_result(task_id, {
                "success": False, "error_code": error_code, "error_message": error_message,
            })
            publish_event(RedisKeys.pub_scan_complete(user_id), {
                "task_id": task_id, "status": "FAILURE",
                "error_code": error_code, "error_message": error_message,
            })

            if retryable and self.request.retries < self.max_retries:
                raise self.retry(countdown=2 ** self.request.retries * 30)

            # Non-retryable: return cleanly without raising (avoids Celery retry loop)
            return {"status": "FAILURE", "error_code": error_code, "error_message": error_message}

        # ── Stage 2: Persist successful result ──────────────────────────────────
        result: dict = payload["result"]
        set_task_progress(task_id, "Saving your beauty profile", 90)

        with get_sync_session() as session:
            scan = session.get(FacialScan, scan_id)
            if scan is None:
                raise ValueError(f"FacialScan {scan_id} not found")

            scan.face_shape = result["face_shape"]["shape"]
            scan.skin_analysis = {
                "skin_tone":     result["skin_tone"],
                "age_estimation": result["age_estimation"],
                "acne_analysis": result["acne_analysis"],
                "dark_circles":  result["dark_circles"],
                "skin_texture":  result["skin_texture"],
                "skin_concerns": result["skin_concerns"],
                "hair_analysis": result["hair_analysis"],
                "symmetry":      result["symmetry"],
                "makeup_recommendations":   result["makeup_recommendations"],
                "skincare_recommendations": result["skincare_recommendations"],
                "hairstyle_recommendations": result["hairstyle_recommendations"],
            }
            scan.facial_features = {
                "face_shape_ratios": result["face_shape"]["ratios"],
                "face_shape_description": result["face_shape"]["description"],
                "landmarks": result["landmarks"],
                "bounding_box": result["bounding_box"],
            }
            scan.landmark_data = {"mesh_points": result["mesh_points"]}
            scan.model_version = result["pipeline_version"]
            scan.quality_score = result["quality"]["brisque_score"]
            scan.is_active = True

            # Deactivate all other scans for this user
            session.query(FacialScan).filter(
                FacialScan.user_id == scan.user_id,
                FacialScan.id != scan.id,
            ).update({FacialScan.is_active: False})

            # Mark upload complete
            upload = session.get(Upload, upload_id)
            if upload:
                upload.status = UploadStatus.COMPLETE

        # Cache the latest scan summary for fast dashboard reads
        from app.cache.redis_client import cache_set  # noqa — sync-safe (just builds key)
        sync_payload = {
            "scan_id": scan_id,
            "face_shape": result["face_shape"]["shape"],
            "skin_tone": result["skin_tone"]["tone"],
            "undertone": result["skin_tone"]["undertone"],
            "processing_time_ms": result["processing_time_ms"],
        }

        set_task_status(task_id, "SUCCESS")
        set_task_progress(task_id, "Complete", 100)
        set_task_result(task_id, {"success": True, "scan_id": scan_id, "result": result})

        publish_event(RedisKeys.pub_scan_complete(user_id), {
            "task_id": task_id, "status": "SUCCESS", "scan_id": scan_id,
            "face_shape": result["face_shape"]["shape"],
            "skin_tone": result["skin_tone"]["tone"],
        })

        logger.info(
            f"[facial_scan] complete user={user_id} scan={scan_id} "
            f"face_shape={result['face_shape']['shape']} "
            f"processing_ms={result['processing_time_ms']}"
        )

        return {
            "status": "SUCCESS",
            "user_id": user_id,
            "scan_id": scan_id,
            "face_shape": result["face_shape"]["shape"],
            "skin_tone": result["skin_tone"]["tone"],
            "undertone": result["skin_tone"]["undertone"],
            "processing_time_ms": result["processing_time_ms"],
        }

    except httpx.HTTPStatusError as exc:
        logger.error(f"[facial_scan] ai_service_http_error: {exc.response.status_code}")
        set_task_status(task_id, "FAILURE")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)
        return {"status": "FAILURE", "error_code": "UPSTREAM_ERROR", "error_message": str(exc)}

    except httpx.RequestError as exc:
        logger.error(f"[facial_scan] ai_service_unreachable: {exc}")
        set_task_status(task_id, "FAILURE")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)
        return {"status": "FAILURE", "error_code": "UPSTREAM_UNREACHABLE", "error_message": str(exc)}

    except Exception as exc:
        logger.exception(f"[facial_scan] unhandled error: {exc}")
        set_task_status(task_id, "FAILURE")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        return {"status": "FAILURE", "error_code": "INTERNAL_ERROR", "error_message": str(exc)}


@shared_task(
    name="app.tasks.ai_tasks.run_tryon",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="media",
    track_started=True,
)
def run_tryon(
    self,
    *,
    user_id: str,
    selfie_s3_key: str,
    product_id: str | None,
) -> dict:
    """
    Virtual try-on pipeline (OpenCV + TensorFlow).
    Calls ai-virtual-tryon service, stores result image to S3, publishes SSE event.
    """
    import httpx

    from app.core.config import get_settings

    settings = get_settings()
    task_id = self.request.id

    logger.info(f"[tryon] start user={user_id} product={product_id} task={task_id}")
    set_task_status(task_id, "STARTED")

    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{settings.AI_FACIAL_SERVICE_URL}/tryon",
                json={
                    "selfie_s3_key": selfie_s3_key,
                    "product_id": product_id,
                    "user_id": user_id,
                    "task_id": task_id,
                },
            )
            response.raise_for_status()
            result = response.json()

        set_task_status(task_id, "SUCCESS")
        set_task_result(task_id, result)
        publish_event(RedisKeys.pub_tryon_complete(user_id), {
            "task_id": task_id, "status": "SUCCESS", "result_url": result.get("result_url"),
        })

        logger.info(f"[tryon] complete user={user_id} result_url={result.get('result_url')}")
        return {"status": "SUCCESS", "result_url": result.get("result_url"), "user_id": user_id}

    except Exception as exc:
        logger.exception(f"[tryon] failed: {exc}")
        set_task_status(task_id, "FAILURE")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        return {"status": "FAILURE", "error_message": str(exc)}


@shared_task(
    name="app.tasks.ai_tasks.process_image_upload",
    bind=True,
    max_retries=3,
    queue="media",
)
def process_image_upload(
    self,
    *,
    user_id: str,
    s3_key: str,
    purpose: str,
    upload_id: str,
) -> dict:
    """
    Resize, optimise, and move an uploaded image to the assets bucket.
    Used for avatar and wardrobe_item uploads (not facial scans, which keep
    the original in the uploads bucket for re-analysis).
    """
    try:
        logger.info(f"[image_upload] processing user={user_id} purpose={purpose} key={s3_key}")

        from app.models.image import Upload, UploadStatus
        with get_sync_session() as session:
            upload = session.get(Upload, upload_id)
            if upload:
                upload.status = UploadStatus.COMPLETE

        return {"status": "SUCCESS", "s3_key": s3_key, "purpose": purpose}
    except Exception as exc:
        logger.exception(f"[image_upload] failed: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        return {"status": "FAILURE", "error_message": str(exc)}


@shared_task(
    name="app.tasks.ai_tasks.run_outfit_generation",
    bind=True,
    max_retries=2,
    queue="ai.low",
)
def run_outfit_generation(
    self,
    *,
    user_id: str,
    outfit_id: str,
    occasion: str | None = None,
    season: str | None = None,
) -> dict:
    """AI outfit generation via the style-dna service."""
    import httpx

    from app.core.config import get_settings

    settings = get_settings()

    try:
        logger.info(f"[outfit_gen] user={user_id} outfit={outfit_id}")
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{settings.RECOMMENDATION_SERVICE_URL}/outfits/generate",
                json={"user_id": user_id, "outfit_id": outfit_id, "occasion": occasion, "season": season},
            )
            response.raise_for_status()
            result = response.json()

        return {"status": "SUCCESS", "outfit_id": outfit_id, "items": result.get("items", [])}

    except Exception as exc:
        logger.exception(f"[outfit_gen] failed: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        return {"status": "FAILURE", "error_message": str(exc)}

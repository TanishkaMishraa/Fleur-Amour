"""
AuraFit — Presigned upload endpoints (/api/v1/uploads/*).
Clients upload directly to S3; backend manages presigned URLs and task dispatch.
Binary data NEVER passes through this service.
"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.v1.dependencies import CurrentUser, UploadServiceDep
from app.schemas.base import APIResponse
from app.schemas.upload import (
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    PresignRequest,
    PresignResponse,
)

router = APIRouter(prefix="/uploads", tags=["File Uploads"])


@router.post(
    "/presign",
    response_model=APIResponse[PresignResponse],
    status_code=status.HTTP_200_OK,
    summary="Request presigned S3 PUT URL",
    description=(
        "Step 1 of the direct-to-S3 upload flow. "
        "Returns a presigned PUT URL valid for 5 minutes. "
        "Client PUTs the binary directly to S3, then calls /uploads/{upload_id}/confirm."
    ),
)
async def request_presign(
    payload: PresignRequest,
    current_user: CurrentUser,
    svc: UploadServiceDep,
) -> APIResponse[PresignResponse]:
    result = await svc.generate_presigned_url(
        user_id=current_user.id,
        file_type=payload.file_type,
        size_bytes=payload.size_bytes,
        purpose=payload.purpose,
    )
    return APIResponse(data=PresignResponse(**result))


@router.post(
    "/{upload_id}/confirm",
    response_model=APIResponse[ConfirmUploadResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Confirm upload complete and dispatch processing task",
    description=(
        "Step 2 of the upload flow. "
        "Validates S3 key matches the upload record, updates status to UPLOADED, "
        "and dispatches the appropriate Celery task (facial scan, avatar resize, etc). "
        "Returns task_id for polling."
    ),
)
async def confirm_upload(
    upload_id: str,
    payload: ConfirmUploadRequest,
    current_user: CurrentUser,
    svc: UploadServiceDep,
) -> APIResponse[ConfirmUploadResponse]:
    result = await svc.confirm_upload(
        upload_id=upload_id,
        user_id=current_user.id,
        s3_key=payload.s3_key,
        purpose=payload.purpose,
    )
    return APIResponse(data=ConfirmUploadResponse(**result))

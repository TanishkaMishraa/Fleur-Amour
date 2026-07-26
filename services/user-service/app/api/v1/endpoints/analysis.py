"""
AuraFit — Facial scan and skin analysis endpoints (/api/v1/analysis/*).
All analysis operations are async: endpoint dispatches Celery task,
client polls /analysis/tasks/{task_id} for results.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.v1.dependencies import AnalysisServiceDep, CurrentUser
from app.core.errors import NotFoundError
from app.schemas.analysis import (
    FacialScanOut,
    ScanInitRequest,
    TaskStatusResponse,
    TryonInitRequest,
)
from app.schemas.base import APIResponse

router = APIRouter(prefix="/analysis", tags=["Skin & Facial Analysis"])


@router.post(
    "/facial-scan",
    response_model=APIResponse[TaskStatusResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate AI facial scan (async)",
    description=(
        "Dispatches the facial analysis pipeline (DeepFace + MediaPipe) as a background task. "
        "Requires the selfie to already be uploaded to S3 via the /uploads presign flow. "
        "Poll /analysis/tasks/{task_id} for completion."
    ),
)
async def initiate_facial_scan(
    payload: ScanInitRequest,
    current_user: CurrentUser,
    svc: AnalysisServiceDep,
) -> APIResponse[TaskStatusResponse]:
    task_info = await svc.initiate_facial_scan(
        user_id=current_user.id,
        s3_key=payload.s3_key,
        upload_id=payload.upload_id,
    )
    return APIResponse(data=TaskStatusResponse(**task_info))


@router.get(
    "/tasks/{task_id}",
    response_model=APIResponse[TaskStatusResponse],
    summary="Poll async task status",
    description="Returns current status, progress (0–100), and result payload when complete.",
)
async def get_task_status(
    task_id: str,
    current_user: CurrentUser,
    svc: AnalysisServiceDep,
) -> APIResponse[TaskStatusResponse]:
    task_info = await svc.get_task_status(task_id)
    return APIResponse(data=TaskStatusResponse(**task_info))


@router.get(
    "/scans",
    response_model=APIResponse[list[FacialScanOut]],
    summary="List my facial scans",
)
async def list_scans(
    current_user: CurrentUser,
    svc: AnalysisServiceDep,
) -> APIResponse[list[FacialScanOut]]:
    scans = await svc.list_scans(current_user.id)
    return APIResponse(data=[FacialScanOut.model_validate(s) for s in scans])


@router.get(
    "/scans/latest",
    response_model=APIResponse[FacialScanOut | None],
    summary="Get most recent active facial scan",
)
async def get_latest_scan(
    current_user: CurrentUser,
    svc: AnalysisServiceDep,
) -> APIResponse[FacialScanOut | None]:
    scan = await svc.get_latest_scan(current_user.id)
    return APIResponse(data=FacialScanOut.model_validate(scan) if scan else None)


@router.get(
    "/scans/{scan_id}",
    response_model=APIResponse[FacialScanOut],
    summary="Get a single facial scan by ID",
    description=(
        "Returns the full stored analysis result for one scan, including "
        "skin_analysis (tone, undertone, acne, dark circles, texture, hair, "
        "age, symmetry, and recommendations) and facial_features (landmarks, "
        "face shape ratios). Scoped to the requesting user."
    ),
)
async def get_scan(
    scan_id: UUID,
    current_user: CurrentUser,
    svc: AnalysisServiceDep,
) -> APIResponse[FacialScanOut]:
    try:
        scan = await svc.get_scan_by_id(current_user.id, scan_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        )
    return APIResponse(data=FacialScanOut.model_validate(scan))


@router.post(
    "/virtual-tryon",
    response_model=APIResponse[TaskStatusResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start virtual try-on (async)",
    description=(
        "Dispatches the virtual try-on pipeline (OpenCV + TensorFlow). "
        "Requires selfie already uploaded to S3. "
        "Poll /analysis/tasks/{task_id} for the result image URL."
    ),
)
async def initiate_virtual_tryon(
    payload: TryonInitRequest,
    current_user: CurrentUser,
    svc: AnalysisServiceDep,
) -> APIResponse[TaskStatusResponse]:
    task_info = await svc.initiate_tryon(
        user_id=current_user.id,
        selfie_s3_key=payload.selfie_s3_key,
        product_id=payload.product_id,
    )
    return APIResponse(data=TaskStatusResponse(**task_info))

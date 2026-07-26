"""
AuraFit — Admin API endpoints (Stage 10).
All routes require ADMIN role. Returns platform analytics, user management,
product management, AI pipeline monitoring, and recommendation performance.

Routes:
  GET  /admin/dashboard         — platform metrics overview
  GET  /admin/users             — list users with filtering/search
  GET  /admin/users/{id}        — user detail + all linked data
  PATCH/admin/users/{id}/role   — update user role
  DELETE /admin/users/{id}      — soft delete user
  GET  /admin/analytics/revenue — revenue/subscription analytics
  GET  /admin/analytics/ai      — AI pipeline performance metrics
  GET  /admin/analytics/recs    — recommendation engine performance
  GET  /admin/queue/status      — Celery queue status
  POST /admin/queue/flush       — flush stale queue tasks
  GET  /admin/products          — product catalog overview (cross-service)
  GET  /admin/reports/daily     — daily business report
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, text

from app.api.v1.dependencies import CurrentUser, DbSession
from app.cache.redis_client import get_redis
from app.core.errors import PermissionDeniedError
from app.core.permissions import Permission, assert_permission
from app.models.analysis import FacialScan
from app.models.color import ColorProfile
from app.models.style_dna import QuizSession, StyleDNAReport
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Admin role required"},
        )


# ── Dashboard overview ─────────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    summary="Platform metrics dashboard",
)
async def admin_dashboard(
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    _require_admin(current_user)

    now = datetime.now(UTC)
    d7  = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    # User stats
    total_users  = (await session.execute(select(func.count(User.id)))).scalar_one()
    new_7d       = (await session.execute(
        select(func.count(User.id)).where(User.created_at >= d7)
    )).scalar_one()
    verified     = (await session.execute(
        select(func.count(User.id)).where(User.is_verified == True)  # noqa: E712
    )).scalar_one()

    # AI usage stats
    total_scans  = (await session.execute(select(func.count(FacialScan.id)))).scalar_one()
    scans_7d     = (await session.execute(
        select(func.count(FacialScan.id)).where(FacialScan.created_at >= d7)
    )).scalar_one()

    total_colors = (await session.execute(select(func.count(ColorProfile.id)))).scalar_one()
    total_dna    = (await session.execute(select(func.count(StyleDNAReport.id)))).scalar_one()
    total_quizzes= (await session.execute(select(func.count(QuizSession.id)))).scalar_one()

    # Queue stats via Redis
    try:
        redis  = await get_redis()
        queues = {
            "default":        int(await redis.llen("celery:default") or 0),
            "ai.high":        int(await redis.llen("celery:ai.high") or 0),
            "ai.low":         int(await redis.llen("celery:ai.low") or 0),
            "recommendations":int(await redis.llen("celery:recommendations") or 0),
            "media":          int(await redis.llen("celery:media") or 0),
        }
    except Exception:
        queues = {}

    return {
        "generated_at": now.isoformat(),
        "users": {
            "total":      total_users,
            "new_7d":     new_7d,
            "verified":   verified,
            "unverified": total_users - verified,
        },
        "ai_usage": {
            "facial_scans_total": total_scans,
            "facial_scans_7d":    scans_7d,
            "color_profiles":     total_colors,
            "style_dna_reports":  total_dna,
            "quizzes_completed":  total_quizzes,
        },
        "celery_queues": queues,
        "platform": {
            "version":     "1.0.0",
            "environment": "production",
        },
    }


# ── User management ────────────────────────────────────────────────────────────

@router.get("/users", summary="List all users")
async def list_users(
    current_user: CurrentUser,
    session:      DbSession,
    q:            str | None = Query(None, description="Search by email or name"),
    role:         str | None = Query(None, description="Filter by role"),
    verified:     bool | None = Query(None),
    page:         int = Query(1, ge=1),
    per_page:     int = Query(50, ge=1, le=200),
) -> dict:
    _require_admin(current_user)

    query = select(User).where(User.is_deleted == False)   # noqa: E712

    if q:
        query = query.where(
            User.email.ilike(f"%{q}%") | User.full_name.ilike(f"%{q}%")
        )
    if role:
        query = query.where(User.role == role)
    if verified is not None:
        query = query.where(User.is_verified == verified)

    total = (await session.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar_one()

    query = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    users = (await session.execute(query)).scalars().all()

    return {
        "users":       [
            {
                "id":         str(u.id),
                "email":      u.email,
                "full_name":  u.full_name,
                "role":       u.role.value,
                "is_active":  u.is_active,
                "is_verified":u.is_verified,
                "mfa_enabled":u.mfa_enabled,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ],
        "total":      total,
        "page":       page,
        "per_page":   per_page,
        "total_pages":max(1, (total + per_page - 1) // per_page),
    }


class RoleUpdateRequest(BaseModel):
    role: str


@router.patch("/users/{user_id}/role", summary="Update user role")
async def update_user_role(
    user_id:      UUID,
    payload:      RoleUpdateRequest,
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    _require_admin(current_user)
    if str(user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        user.role = UserRole(payload.role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid role: {payload.role}")

    session.add(user)
    return {"status": "ok", "user_id": str(user_id), "new_role": user.role.value}


@router.delete("/users/{user_id}", summary="Soft delete user")
async def delete_user(
    user_id:      UUID,
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    _require_admin(current_user)
    if str(user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_deleted  = True
    user.is_active   = False
    user.deleted_at  = datetime.now(UTC)
    session.add(user)
    return {"status": "ok", "message": f"User {user_id} soft-deleted"}


# ── AI analytics ─────────────────────────────────────────────────────────────

@router.get("/analytics/ai", summary="AI pipeline performance metrics")
async def ai_analytics(
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    _require_admin(current_user)

    now = datetime.now(UTC)
    d7  = now - timedelta(days=7)

    # Scan quality distribution
    quality_result = await session.execute(text("""
        SELECT
            AVG(quality_score) as avg_quality,
            MIN(quality_score) as min_quality,
            MAX(quality_score) as max_quality,
            COUNT(*) as total
        FROM facial_scans
        WHERE created_at >= :cutoff AND quality_score IS NOT NULL
    """), {"cutoff": d7})
    quality = quality_result.fetchone()

    # Face shape distribution
    shape_result = await session.execute(text("""
        SELECT face_shape, COUNT(*) as count
        FROM facial_scans
        WHERE face_shape IS NOT NULL
        GROUP BY face_shape
        ORDER BY count DESC
    """))
    shape_dist = {row[0]: row[1] for row in shape_result.fetchall()}

    # Color season distribution
    season_result = await session.execute(text("""
        SELECT season, COUNT(*) as count
        FROM color_profiles
        WHERE is_active = true
        GROUP BY season
        ORDER BY count DESC
    """))
    season_dist = {row[0]: row[1] for row in season_result.fetchall()}

    return {
        "period": "last_7_days",
        "scan_quality": {
            "avg":   round(float(quality[0] or 0), 3),
            "min":   round(float(quality[1] or 0), 3),
            "max":   round(float(quality[2] or 0), 3),
            "total": int(quality[3] or 0),
        },
        "face_shape_distribution": shape_dist,
        "color_season_distribution": season_dist,
    }


@router.get("/analytics/recs", summary="Recommendation engine performance")
async def rec_analytics(
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    _require_admin(current_user)
    return {
        "note": "Recommendation analytics served by recommendation-service.",
        "endpoint": "GET http://recommendation-service:8003/api/v1/admin/analytics",
    }


# ── Queue management ───────────────────────────────────────────────────────────

@router.get("/queue/status", summary="Celery queue depths")
async def queue_status(current_user: CurrentUser) -> dict:
    _require_admin(current_user)
    try:
        redis = await get_redis()
        queues_to_check = [
            "celery:default", "celery:ai.high", "celery:ai.low",
            "celery:recommendations", "celery:media", "celery:maintenance",
        ]
        depths = {}
        for q in queues_to_check:
            name         = q.replace("celery:", "")
            depths[name] = int(await redis.llen(q) or 0)
        return {"queues": depths, "checked_at": datetime.now(UTC).isoformat()}
    except Exception as exc:
        return {"error": str(exc), "queues": {}}


# ── Daily report ───────────────────────────────────────────────────────────────

@router.get("/reports/daily", summary="Daily platform report")
async def daily_report(
    current_user: CurrentUser,
    session:      DbSession,
) -> dict:
    _require_admin(current_user)

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    new_users_today = (await session.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )).scalar_one()

    scans_today = (await session.execute(
        select(func.count(FacialScan.id)).where(FacialScan.created_at >= today_start)
    )).scalar_one()

    dna_today = (await session.execute(
        select(func.count(StyleDNAReport.id)).where(StyleDNAReport.created_at >= today_start)
    )).scalar_one()

    return {
        "date":           today_start.date().isoformat(),
        "new_users":      new_users_today,
        "facial_scans":   scans_today,
        "style_dna_reports": dna_today,
        "generated_at":   now.isoformat(),
    }

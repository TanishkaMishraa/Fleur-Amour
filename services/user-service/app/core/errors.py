"""
AuraFit — Centralised error handling.
All exceptions map to the Stage 0 error envelope:
{ "success": false, "data": null, "errors": [{ "code", "field", "message" }] }

Domain exceptions (AuthenticationError etc.) are raised in service layer.
Global exception handlers in register_exception_handlers() convert them to HTTP responses.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Stable error code contract ────────────────────────────────────────────────
class ErrorCode(StrEnum):
    # Auth
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    # Resource
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    # Permissions
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ROLE_REQUIRED = "ROLE_REQUIRED"
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"
    AI_QUOTA_EXCEEDED = "AI_QUOTA_EXCEEDED"
    # Upstream / async
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BAD_REQUEST = "BAD_REQUEST"


# ── Domain exception hierarchy ────────────────────────────────────────────────

class AuraFitError(Exception):
    """Base for all AuraFit domain errors. Always has a code + message."""
    code: str = ErrorCode.INTERNAL_ERROR
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class AuthenticationError(AuraFitError):
    code = ErrorCode.INVALID_CREDENTIALS
    http_status = status.HTTP_401_UNAUTHORIZED


class AccountLockedError(AuraFitError):
    code = ErrorCode.ACCOUNT_LOCKED
    http_status = status.HTTP_423_LOCKED


class TokenError(AuraFitError):
    code = ErrorCode.TOKEN_INVALID
    http_status = status.HTTP_401_UNAUTHORIZED


class NotFoundError(AuraFitError):
    code = ErrorCode.NOT_FOUND
    http_status = status.HTTP_404_NOT_FOUND


class AlreadyExistsError(AuraFitError):
    code = ErrorCode.ALREADY_EXISTS
    http_status = status.HTTP_409_CONFLICT


class PermissionDeniedError(AuraFitError):
    code = ErrorCode.PERMISSION_DENIED
    http_status = status.HTTP_403_FORBIDDEN


class RateLimitedError(AuraFitError):
    code = ErrorCode.RATE_LIMITED
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


class ValidationError(AuraFitError):
    code = ErrorCode.VALIDATION_ERROR
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class UpstreamError(AuraFitError):
    code = ErrorCode.UPSTREAM_ERROR
    http_status = status.HTTP_502_BAD_GATEWAY


# ── Response builder ──────────────────────────────────────────────────────────

def _error_body(errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {"success": False, "data": None, "errors": errors}


def _json(status_code: int, errors: list[dict[str, Any]]) -> ORJSONResponse:
    return ORJSONResponse(status_code=status_code, content=_error_body(errors))


# ── Handler registration ──────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app instance."""

    @app.exception_handler(AuraFitError)
    async def aurafit_error_handler(request: Request, exc: AuraFitError) -> ORJSONResponse:
        logger.warning(
            "aurafit.domain_error",
            code=exc.code,
            message=exc.message,
            path=str(request.url),
        )
        return _json(
            exc.http_status,
            [{"code": exc.code, "field": exc.field, "message": exc.message}],
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        errors = [
            {
                "code": ErrorCode.VALIDATION_ERROR,
                "field": ".".join(str(loc) for loc in e["loc"][1:]) or None,
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        logger.warning(
            "aurafit.validation_error",
            errors=errors,
            path=str(request.url),
        )
        return _json(status.HTTP_422_UNPROCESSABLE_ENTITY, errors)

    @app.exception_handler(IntegrityError)
    async def db_integrity_handler(
        request: Request, exc: IntegrityError
    ) -> ORJSONResponse:
        logger.warning("aurafit.db_integrity_error", error=str(exc))
        return _json(
            status.HTTP_409_CONFLICT,
            [{"code": ErrorCode.CONFLICT, "field": None,
              "message": "A conflicting record already exists"}],
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> ORJSONResponse:
        return _json(
            status.HTTP_400_BAD_REQUEST,
            [{"code": ErrorCode.BAD_REQUEST, "field": None, "message": str(exc)}],
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> ORJSONResponse:
        logger.exception(
            "aurafit.unhandled_error",
            exc_info=exc,
            path=str(request.url),
        )
        return _json(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            [{"code": ErrorCode.INTERNAL_ERROR, "field": None,
              "message": "An unexpected error occurred"}],
        )

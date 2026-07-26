"""
AuraFit - Global exception handlers.
Registered on the FastAPI app. Converts exceptions to standard error envelope.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(status_code: int, errors: list[dict]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None, "errors": errors},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            errors = [detail]
        else:
            errors = [{"code": "HTTP_ERROR", "message": str(detail)}]
        return _error_response(exc.status_code, errors)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "code": "VALIDATION_ERROR",
                "field": ".".join(str(loc) for loc in e["loc"][1:]),
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        logger.warning("aurafit.validation_error", errors=errors, path=str(request.url))
        return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, errors)

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("aurafit.value_error", error=str(exc), path=str(request.url))
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            [{"code": "BAD_REQUEST", "message": str(exc)}],
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("aurafit.unhandled_error", exc_info=exc, path=str(request.url))
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            [{"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}],
        )

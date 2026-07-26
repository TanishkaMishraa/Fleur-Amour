"""
AuraFit - Common response envelope schemas.
All API responses use these wrappers (Stage 0 spec).
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    code: str
    field: str | None = None
    message: str


class ApiResponse(BaseModel, Generic[DataT]):
    """Standard single-item response envelope."""
    success: bool = True
    data: DataT | None = None
    errors: list[ErrorDetail] | None = None

    @classmethod
    def ok(cls, data: DataT) -> "ApiResponse[DataT]":
        return cls(success=True, data=data)

    @classmethod
    def error(cls, errors: list[ErrorDetail]) -> "ApiResponse[Any]":
        return cls(success=False, data=None, errors=errors)


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Standard paginated response envelope."""
    success: bool = True
    data: list[DataT]
    meta: PaginationMeta
    errors: list[ErrorDetail] | None = None

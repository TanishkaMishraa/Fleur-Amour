"""AuraFit — Base Pydantic schemas shared across all endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class AuraFitSchema(BaseModel):
    """Root schema. All request/response schemas inherit from this."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(AuraFitSchema):
    created_at: datetime
    updated_at: datetime


class UUIDSchema(AuraFitSchema):
    id: UUID


class APIResponse(AuraFitSchema, Generic[DataT]):
    """Standard envelope for all API responses."""
    success: bool = True
    data: DataT | None = None
    message: str | None = None


class PaginatedMeta(AuraFitSchema):
    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(AuraFitSchema, Generic[DataT]):
    """Standard envelope for paginated list responses."""
    success: bool = True
    data: list[DataT]
    meta: PaginatedMeta


class ErrorDetail(AuraFitSchema):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(AuraFitSchema):
    success: bool = False
    errors: list[ErrorDetail]
    data: None = None

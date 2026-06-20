"""Shared / generic Pydantic schemas used across the API."""

from __future__ import annotations

from typing import Any, Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    """Simple message-only response."""

    message: str


class ErrorResponse(BaseModel):
    """Standardised error envelope."""

    detail: str
    code: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper for paginated list responses."""

    items: List[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0

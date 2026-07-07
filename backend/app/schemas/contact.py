"""Contact form schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ContactSubmit(BaseModel):
    name: str = Field(..., max_length=200)
    email: str | None = None
    phone: str | None = Field(None, max_length=20)
    message: str = Field(..., max_length=5000)


class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}

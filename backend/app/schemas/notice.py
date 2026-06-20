"""Notice schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class NoticeCreate(BaseModel):
    """Payload for composing a notice."""

    title: str = Field(..., max_length=255)
    content: str
    attachment_url: str | None = None
    audience: str = Field(default="everyone", pattern="^(everyone|class|staff)$")
    target_class_id: int | None = None
    channels: List[str] = Field(default_factory=lambda: ["app"])
    scheduled_at: datetime | None = None


class NoticeResponse(BaseModel):
    """Notice returned in responses."""

    id: int
    title: str
    content: str
    attachment_url: str | None = None
    audience: str
    target_class_id: int | None = None
    channels: list | None = None
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    created_by_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

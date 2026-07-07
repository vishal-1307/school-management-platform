"""Student and Parent schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field


# ── Parent ──────────────────────────────────────────────────────────────


class ParentBase(BaseModel):
    """Shared parent fields."""

    name: str = Field(..., max_length=200)
    phone: str = Field(..., max_length=20)
    email: str | None = None
    whatsapp_number: str | None = None
    relation: str = Field(..., max_length=30)


class ParentCreate(ParentBase):
    """Payload for adding a parent to a student."""

    pass


class ParentResponse(ParentBase):
    """Parent data returned in responses."""

    id: int
    student_id: int

    model_config = {"from_attributes": True}


# ── Student ─────────────────────────────────────────────────────────────


class StudentCreate(BaseModel):
    """Payload for creating a new student."""

    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    dob: date
    gender: str = Field(..., max_length=10)
    photo_url: str | None = None
    class_id: int
    section_id: int
    roll_number: int | None = None
    address: str | None = None
    documents: dict | None = None
    parents: List[ParentCreate] = Field(default_factory=list)


class StudentUpdate(BaseModel):
    """Partial update payload for a student."""

    first_name: str | None = None
    last_name: str | None = None
    dob: date | None = None
    gender: str | None = None
    photo_url: str | None = None
    class_id: int | None = None
    section_id: int | None = None
    roll_number: int | None = None
    address: str | None = None
    documents: dict | None = None
    is_active: bool | None = None


class StudentResponse(BaseModel):
    """Full student data returned in responses."""

    id: int
    admission_number: str
    first_name: str
    last_name: str
    dob: date
    gender: str
    photo_url: str | None = None
    class_id: int
    section_id: int
    roll_number: int | None = None
    address: str | None = None
    documents: dict | None = None
    is_active: bool
    created_at: datetime
    parents: List[ParentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class StudentListResponse(BaseModel):
    """Paginated list of students."""

    items: List[StudentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkImportResponse(BaseModel):
    """Result of a bulk student import."""

    imported: int = 0
    skipped: int = 0
    errors: List[str] = Field(default_factory=list)


class PromoteClassRequest(BaseModel):
    """Promote every active student of one class into another (SRS 6.2)."""

    from_class_id: int
    to_class_id: int
    to_section_id: int


class PromoteClassResponse(BaseModel):
    promoted: int

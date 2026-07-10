"""Admission enquiry schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class EnquirySubmit(BaseModel):
    """Public-facing enquiry form submission (no auth required)."""

    child_name: str = Field(..., max_length=200)
    dob: date | None = None
    class_applying: str = Field(..., max_length=30)
    parent_name: str = Field(..., max_length=200)
    phone: str = Field(..., max_length=20)
    email: str | None = Field(None, max_length=255)
    address: str | None = Field(None, max_length=500)
    source: str | None = Field(None, max_length=100)
    message: str | None = Field(None, max_length=2000)


class EnquiryUpdate(BaseModel):
    """Admin update to move an enquiry through the pipeline."""

    status: str = Field(..., pattern="^(new|contacted|visited|admitted|not_interested)$")
    notes: str | None = None


class EnquiryResponse(BaseModel):
    """Enquiry details returned in admin views."""

    id: int
    child_name: str
    dob: date | None = None
    class_applying: str
    parent_name: str
    phone: str
    email: str | None = None
    address: str | None = None
    source: str | None = None
    message: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnquiryListResponse(BaseModel):
    """Paginated list of admission enquiries."""

    items: list[EnquiryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

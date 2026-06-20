"""Staff schemas."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class StaffSubjectAssignmentSchema(BaseModel):
    """Subject-class-section teaching assignment."""

    subject_id: int
    class_id: int
    section_id: int


class StaffCreate(BaseModel):
    """Payload for creating a new staff member."""

    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    email: str | None = None
    photo_url: str | None = None
    qualification: str | None = None
    designation: str | None = None
    assignments: List[StaffSubjectAssignmentSchema] = Field(default_factory=list)


class StaffUpdate(BaseModel):
    """Partial update payload for a staff member."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    photo_url: str | None = None
    qualification: str | None = None
    designation: str | None = None
    is_active: bool | None = None


class StaffAssignmentResponse(BaseModel):
    """Assignment detail returned in staff responses."""

    id: int
    subject_id: int
    class_id: int
    section_id: int

    model_config = {"from_attributes": True}


class StaffResponse(BaseModel):
    """Full staff member data."""

    id: int
    first_name: str
    last_name: str
    phone: str
    email: str | None = None
    photo_url: str | None = None
    qualification: str | None = None
    designation: str | None = None
    is_active: bool
    subject_assignments: List[StaffAssignmentResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}

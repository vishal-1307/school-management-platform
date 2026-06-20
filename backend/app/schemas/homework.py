"""Homework schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HomeworkCreate(BaseModel):
    """Payload for assigning homework."""

    class_id: int
    section_id: int
    subject_id: int
    title: str = Field(..., max_length=255)
    description: str | None = None
    attachment_url: str | None = None
    due_date: datetime


class HomeworkResponse(BaseModel):
    """Homework assignment returned in responses."""

    id: int
    class_id: int
    section_id: int
    subject_id: int
    assigned_by_id: int
    title: str
    description: str | None = None
    attachment_url: str | None = None
    due_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class HomeworkSubmissionCreate(BaseModel):
    """Payload for a student submitting homework."""

    homework_id: int
    submission_url: str | None = None


class HomeworkSubmissionResponse(BaseModel):
    """Homework submission returned in responses."""

    id: int
    homework_id: int
    student_id: int
    submission_url: str | None = None
    submitted_at: datetime | None = None
    status: str
    remarks: str | None = None

    model_config = {"from_attributes": True}

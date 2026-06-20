"""Attendance schemas."""

from __future__ import annotations

import datetime
from typing import List

from pydantic import BaseModel, Field


class StudentAttendanceEntry(BaseModel):
    """A single student's status within a bulk mark request."""

    student_id: int
    status: str = Field(..., pattern="^(present|absent|late)$")


class AttendanceMarkRequest(BaseModel):
    """Bulk attendance marking request for a class/section/date."""

    class_id: int
    section_id: int
    date: datetime.date
    period: int | None = None
    entries: List[StudentAttendanceEntry]


class AttendanceOverrideRequest(BaseModel):
    """Request to override a previously-recorded attendance."""

    status: str = Field(..., pattern="^(present|absent|late)$")
    reason: str = Field(..., min_length=5)


class AttendanceResponse(BaseModel):
    """Single attendance record."""

    id: int
    student_id: int
    date: datetime.date
    status: str
    period: int | None = None
    override_reason: str | None = None

    model_config = {"from_attributes": True}


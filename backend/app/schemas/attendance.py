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


class StaffAttendanceEntry(BaseModel):
    """A single staff member's status within a bulk mark request."""

    staff_id: int
    status: str = Field(..., pattern="^(present|absent|late)$")


class StaffAttendanceMarkRequest(BaseModel):
    """Bulk staff attendance marking for a date (SRS 6.3/6.6)."""

    date: datetime.date
    entries: List[StaffAttendanceEntry]


class StaffAttendanceResponse(BaseModel):
    """Single staff attendance record."""

    id: int
    staff_id: int
    date: datetime.date
    status: str

    model_config = {"from_attributes": True}


"""Timetable schemas."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class TimetableSlotCreate(BaseModel):
    """Payload for adding/updating a timetable slot."""

    class_id: int
    section_id: int
    day_of_week: str = Field(..., pattern="^(monday|tuesday|wednesday|thursday|friday|saturday)$")
    period_number: int = Field(..., ge=1, le=12)
    subject_id: int
    staff_id: int
    is_substitute: bool = False


class TimetableSlotResponse(BaseModel):
    """Single timetable slot."""

    id: int
    class_id: int
    section_id: int
    day_of_week: str
    period_number: int
    subject_id: int
    staff_id: int
    is_substitute: bool

    model_config = {"from_attributes": True}


class DaySchedule(BaseModel):
    """All periods for one day."""

    day: str
    slots: List[TimetableSlotResponse]


class WeeklyTimetableResponse(BaseModel):
    """Complete weekly timetable for a class-section."""

    class_id: int
    section_id: int
    schedule: List[DaySchedule]

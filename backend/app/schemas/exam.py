"""Exam and marks schemas."""

from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class ExamSubjectCreate(BaseModel):
    """Subject details within an exam."""

    subject_id: int
    max_marks: float = Field(..., gt=0)
    passing_marks: float = Field(..., ge=0)
    exam_date: date | None = None


class ExamCreate(BaseModel):
    """Payload for creating a new exam."""

    name: str = Field(..., max_length=150)
    academic_year_id: int
    class_id: int
    exam_type: str = Field(..., max_length=30)
    start_date: date
    end_date: date
    subjects: List[ExamSubjectCreate] = Field(default_factory=list)


class MarkEntry(BaseModel):
    """Single student mark entry."""

    student_id: int
    marks_obtained: float | None = None
    grade: str | None = None


class MarksEntryRequest(BaseModel):
    """Bulk marks submission for an exam-subject."""

    exam_subject_id: int
    entries: List[MarkEntry]


class SubjectMarkResponse(BaseModel):
    """A student's mark in one subject."""

    subject_name: str
    subject_code: str
    max_marks: float
    passing_marks: float
    marks_obtained: float | None = None
    grade: str | None = None
    passed: bool = False


class ReportCardResponse(BaseModel):
    """Complete report card for a student in one exam."""

    student_id: int
    student_name: str
    admission_number: str
    class_name: str
    exam_name: str
    subjects: List[SubjectMarkResponse]
    total_marks: float
    total_obtained: float
    percentage: float
    overall_grade: str
    result: str  # "Pass" / "Fail"

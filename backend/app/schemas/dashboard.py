"""Response schemas for the three role dashboards.

Every field here is computed from real rows at request time — there is no
placeholder/demo value baked into the response shape itself.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


# ── Student ──────────────────────────────────────────────────────────────


class TimetablePeriod(BaseModel):
    period_number: int
    subject_name: str
    # Student's schedule: the teacher's name. Teacher's own schedule: which
    # class/section they're teaching. Same shape, context-dependent label.
    subtitle: str
    is_current: bool


class LatestResult(BaseModel):
    exam_name: str
    published: bool
    percentage: float | None = None
    grade: str | None = None


class DashboardNotice(BaseModel):
    id: int
    title: str
    published_at: datetime | None = None


class StudentDashboardResponse(BaseModel):
    attendance_percentage: float | None
    pending_homework_count: int
    latest_result: LatestResult | None
    fee_due: float
    today_timetable: list[TimetablePeriod]
    recent_notices: list[DashboardNotice]
    generated_at: datetime


# ── Teacher ──────────────────────────────────────────────────────────────


class ClassSectionRef(BaseModel):
    class_id: int
    section_id: int
    class_name: str
    section_name: str


class AttendanceStatusSummary(BaseModel):
    all_marked: bool
    pending: list[ClassSectionRef]


class MyClassChip(BaseModel):
    class_name: str
    section_name: str
    subject_name: str


class PendingMarksRow(BaseModel):
    # Exams target a whole class, not a section, so there is no section here.
    exam_id: int
    exam_subject_id: int
    exam_name: str
    subject_name: str
    class_name: str
    entered_count: int
    total_students: int


class TeacherDashboardResponse(BaseModel):
    today_schedule: list[TimetablePeriod]
    attendance_status: AttendanceStatusSummary
    homework_to_review_count: int
    my_classes: list[MyClassChip]
    latest_notice: DashboardNotice | None
    pending_marks: list[PendingMarksRow]
    generated_at: datetime


# ── Admin ────────────────────────────────────────────────────────────────


class KpiValue(BaseModel):
    value: float
    trend_percent: float | None = None  # None = not computable, never faked


class MonthlyPoint(BaseModel):
    month: str  # "2026-07"
    label: str  # "Jul"
    amount: float


class ClassAttendanceBar(BaseModel):
    class_name: str
    percentage: float


class ActivityItem(BaseModel):
    type: str  # "notice" | "enquiry" | "payment"
    text: str
    at: datetime


class AdminDashboardResponse(BaseModel):
    total_students: KpiValue
    total_staff: KpiValue
    fees_collected: KpiValue
    fees_pending: float
    new_enquiries: int
    fee_collection_by_month: list[MonthlyPoint]
    attendance_by_class: list[ClassAttendanceBar]
    recent_activity: list[ActivityItem]
    generated_at: datetime

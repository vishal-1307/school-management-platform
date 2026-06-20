"""Attendance models for students and staff."""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AttendanceStatus(str, enum.Enum):
    """Possible attendance statuses."""

    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class Attendance(Base):
    """Daily student attendance record."""

    __tablename__ = "attendances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status", create_constraint=True),
        nullable=False,
    )
    marked_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    override_reason: Mapped[str | None] = mapped_column(Text)
    period: Mapped[int | None] = mapped_column(Integer, comment="Period number; NULL = full-day")

    # relationships
    student: Mapped["Student"] = relationship(back_populates="attendances")  # noqa: F821
    marked_by: Mapped["User | None"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Attendance student={self.student_id} date={self.date} status={self.status.value}>"


class StaffAttendance(Base):
    """Daily staff attendance record."""

    __tablename__ = "staff_attendances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status", create_constraint=True, create_type=False),
        nullable=False,
    )

    # relationships
    staff: Mapped["Staff"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<StaffAttendance staff={self.staff_id} date={self.date}>"

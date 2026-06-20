"""Timetable slot model."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimetableSlot(Base):
    """One period in the weekly timetable for a class+section."""

    __tablename__ = "timetable_slots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False, index=True)
    day_of_week: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="monday..saturday",
    )
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    is_substitute: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # relationships
    class_: Mapped["Class"] = relationship(lazy="selectin")  # noqa: F821
    section: Mapped["Section"] = relationship(lazy="selectin")  # noqa: F821
    subject: Mapped["Subject"] = relationship(lazy="selectin")  # noqa: F821
    staff: Mapped["Staff"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<TimetableSlot day={self.day_of_week} period={self.period_number}>"

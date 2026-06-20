"""Exam, ExamSubject and Mark models."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Exam(Base):
    """An examination event for a class in an academic year."""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    exam_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="unit_test/mid_term/final")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    results_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # relationships
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="exams")  # noqa: F821
    class_: Mapped["Class"] = relationship(lazy="selectin")  # noqa: F821
    exam_subjects: Mapped[list["ExamSubject"]] = relationship(
        back_populates="exam", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} name={self.name!r}>"


class ExamSubject(Base):
    """Links an exam to a subject with marks configuration."""

    __tablename__ = "exam_subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    passing_marks: Mapped[float] = mapped_column(Float, nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date)

    # relationships
    exam: Mapped["Exam"] = relationship(back_populates="exam_subjects")
    subject: Mapped["Subject"] = relationship(lazy="selectin")  # noqa: F821
    marks: Mapped[list["Mark"]] = relationship(
        back_populates="exam_subject", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ExamSubject exam={self.exam_id} subject={self.subject_id}>"


class Mark(Base):
    """Individual student marks for an exam-subject."""

    __tablename__ = "marks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    exam_subject_id: Mapped[int] = mapped_column(ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    marks_obtained: Mapped[float | None] = mapped_column(Float)
    grade: Mapped[str | None] = mapped_column(String(5))
    entered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # relationships
    exam_subject: Mapped["ExamSubject"] = relationship(back_populates="marks")
    student: Mapped["Student"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Mark student={self.student_id} marks={self.marks_obtained}>"

"""Homework and HomeworkSubmission models."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubmissionStatus(str, enum.Enum):
    """Submission workflow states."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class Homework(Base):
    """Homework assigned to a class/section."""

    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(512))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    class_: Mapped["Class"] = relationship(lazy="selectin")  # noqa: F821
    section: Mapped["Section"] = relationship(lazy="selectin")  # noqa: F821
    subject: Mapped["Subject"] = relationship(lazy="selectin")  # noqa: F821
    assigned_by: Mapped["Staff"] = relationship(lazy="selectin")  # noqa: F821
    submissions: Mapped[list["HomeworkSubmission"]] = relationship(
        back_populates="homework", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Homework id={self.id} title={self.title!r}>"


class HomeworkSubmission(Base):
    """Student submission for a homework assignment."""

    __tablename__ = "homework_submissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_url: Mapped[str | None] = mapped_column(String(512))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", create_constraint=True),
        default=SubmissionStatus.PENDING,
        server_default="pending",
        nullable=False,
    )
    remarks: Mapped[str | None] = mapped_column(Text)

    # relationships
    homework: Mapped["Homework"] = relationship(back_populates="submissions")
    student: Mapped["Student"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<HomeworkSubmission homework={self.homework_id} student={self.student_id}>"

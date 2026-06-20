"""Staff and StaffSubjectAssignment models."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Staff(Base):
    """Teaching and non-teaching staff member."""

    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    photo_url: Mapped[str | None] = mapped_column(String(512))
    qualification: Mapped[str | None] = mapped_column(String(200))
    designation: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # relationships
    subject_assignments: Mapped[list["StaffSubjectAssignment"]] = relationship(
        back_populates="staff", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Staff id={self.id} name={self.first_name} {self.last_name}>"


class StaffSubjectAssignment(Base):
    """Maps a staff member to a subject for a specific class + section."""

    __tablename__ = "staff_subject_assignments"
    __table_args__ = (
        UniqueConstraint("staff_id", "subject_id", "class_id", "section_id", name="uq_staff_subj_cls_sec"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False)

    # relationships
    staff: Mapped["Staff"] = relationship(back_populates="subject_assignments")
    subject: Mapped["Subject"] = relationship(lazy="selectin")  # noqa: F821
    class_: Mapped["Class"] = relationship(lazy="selectin")  # noqa: F821
    section: Mapped["Section"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<StaffSubjectAssignment staff={self.staff_id} subject={self.subject_id}>"

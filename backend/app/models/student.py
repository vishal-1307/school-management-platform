"""Student and Parent models."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    """Student enrolled in the school."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admission_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True,
        comment="Auto-generated admission number",
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False, comment="male/female/other")
    photo_url: Mapped[str | None] = mapped_column(String(512))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), nullable=False, index=True)
    roll_number: Mapped[int | None] = mapped_column(Integer)
    address: Mapped[str | None] = mapped_column(Text)
    documents: Mapped[dict | None] = mapped_column(JSON, default=dict, comment="ID proofs, birth cert URLs")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    class_: Mapped["Class"] = relationship(back_populates="students")  # noqa: F821
    section: Mapped["Section"] = relationship(back_populates="students")  # noqa: F821
    parents: Mapped[list["Parent"]] = relationship(back_populates="student", lazy="selectin", cascade="all, delete-orphan")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="student", lazy="noload")  # noqa: F821
    fee_transactions: Mapped[list["FeeTransaction"]] = relationship(back_populates="student", lazy="noload")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Student id={self.id} admission={self.admission_number!r}>"


class Parent(Base):
    """Parent / guardian linked to a student."""

    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    relation: Mapped[str] = mapped_column(String(30), nullable=False, comment="father/mother/guardian")
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)

    # relationships
    student: Mapped["Student"] = relationship(back_populates="parents")

    def __repr__(self) -> str:
        return f"<Parent id={self.id} name={self.name!r} student_id={self.student_id}>"

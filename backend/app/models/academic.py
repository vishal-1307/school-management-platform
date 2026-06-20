"""Academic models — AcademicYear, Class, Section, Subject."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AcademicYear(Base):
    """A labelled academic year with start/end dates."""

    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. 2025-26")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # relationships
    fee_structures: Mapped[list["FeeStructure"]] = relationship(  # noqa: F821
        back_populates="academic_year", lazy="selectin",
    )
    exams: Mapped[list["Exam"]] = relationship(back_populates="academic_year", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AcademicYear id={self.id} label={self.label!r}>"


class Class(Base):
    """School class / grade (e.g. Class 1, Class 12)."""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    numeric_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="For sorting")

    # relationships
    sections: Mapped[list["Section"]] = relationship(back_populates="class_", lazy="selectin")
    students: Mapped[list["Student"]] = relationship(back_populates="class_", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Class id={self.id} name={self.name!r}>"


class Section(Base):
    """A section within a class (e.g. 'A', 'B')."""

    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("name", "class_id", name="uq_section_class"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(10), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    class_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"))

    # relationships
    class_: Mapped["Class"] = relationship(back_populates="sections")
    class_teacher: Mapped["Staff | None"] = relationship(lazy="selectin")  # noqa: F821
    students: Mapped[list["Student"]] = relationship(back_populates="section", lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Section id={self.id} name={self.name!r} class_id={self.class_id}>"


class Subject(Base):
    """Academic subject taught in the school."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.code!r}>"

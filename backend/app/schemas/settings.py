"""Settings Pydantic schemas."""

from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field


class SchoolBase(BaseModel):
    name: str = Field(..., max_length=255)
    logo_url: str | None = Field(None, max_length=512)
    address: str | None = None
    affiliation_number: str | None = Field(None, max_length=100)
    contact_email: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=20)
    settings: dict | None = None


class SchoolResponse(SchoolBase):
    id: int

    class Config:
        from_attributes = True


class AcademicYearBase(BaseModel):
    label: str = Field(..., max_length=50, description="e.g. 2025-26")
    start_date: date
    end_date: date
    is_current: bool = False


class AcademicYearCreate(AcademicYearBase):
    pass


class AcademicYearResponse(AcademicYearBase):
    id: int

    class Config:
        from_attributes = True


class ClassBase(BaseModel):
    name: str = Field(..., max_length=50)
    numeric_order: int = Field(..., description="For sorting")


class ClassCreate(ClassBase):
    pass


class ClassResponse(ClassBase):
    id: int

    class Config:
        from_attributes = True


class SectionBase(BaseModel):
    name: str = Field(..., max_length=10)
    class_id: int
    class_teacher_id: int | None = None


class SectionCreate(SectionBase):
    pass


class SectionResponse(SectionBase):
    id: int

    class Config:
        from_attributes = True


class SubjectBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=20)


class SubjectCreate(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: int

    class Config:
        from_attributes = True

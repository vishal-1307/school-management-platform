"""User management schemas (SRS §6.15)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Create a login for a staff member, student, or office admin.

    login_id convention: admission number for students (e.g. ADM-00001),
    employee ID for staff (e.g. EMP-001).
    """

    login_id: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=200)
    role: str = Field(..., pattern="^(super_admin|office_admin|teacher|student|parent)$")
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    linked_staff_id: int | None = None
    linked_student_id: int | None = None
    linked_parent_id: int | None = None
    permissions: dict | None = None


class UserUpdate(BaseModel):
    role: str | None = Field(
        None, pattern="^(super_admin|office_admin|teacher|student|parent)$"
    )
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    linked_staff_id: int | None = None
    linked_student_id: int | None = None
    linked_parent_id: int | None = None
    permissions: dict | None = None


class PasswordReset(BaseModel):
    password: str = Field(..., min_length=8, max_length=200)


class UserAdminResponse(BaseModel):
    """Full user record for the admin's User & Role Management screen."""

    id: int
    login_id: str
    email: str | None = None
    phone: str | None = None
    role: str
    linked_staff_id: int | None = None
    linked_student_id: int | None = None
    linked_parent_id: int | None = None
    is_active: bool
    permissions: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    detail: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

"""User management schemas (SRS §6.15)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, computed_field


class UserCreate(BaseModel):
    """Create a login for a staff member, student, or office admin."""

    role: str = Field(..., pattern="^(super_admin|office_admin|teacher|student|parent)$")
    first_name: str = ""
    last_name: str = ""
    email: str | None = None
    phone: str | None = None
    username: str | None = None
    password: str | None = Field(None, min_length=8)
    linked_staff_id: int | None = None
    linked_student_id: int | None = None
    linked_parent_id: int | None = None
    permissions: dict | None = None


class UserUpdate(BaseModel):
    role: str | None = Field(
        None, pattern="^(super_admin|office_admin|teacher|student|parent)$"
    )
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    linked_staff_id: int | None = None
    linked_student_id: int | None = None
    linked_parent_id: int | None = None
    permissions: dict | None = None


class PasswordReset(BaseModel):
    password: str = Field(..., min_length=8)


class UserAdminResponse(BaseModel):
    """Full user record for the admin's User & Role Management screen."""

    id: int
    clerk_id: str
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

    @computed_field
    @property
    def provisioned(self) -> bool:
        """False while the user only exists locally (no Clerk account yet)."""
        return not self.clerk_id.startswith("pending:")


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    action: str
    entity_type: str | None = None
    entity_id: int | None = None
    detail: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

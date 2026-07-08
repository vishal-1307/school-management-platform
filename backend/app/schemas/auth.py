"""Auth-related schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Institutional login: school-issued ID + password."""

    login_id: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=200)


class UserResponse(BaseModel):
    """User profile returned by /me and inside LoginResponse."""

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


class LoginResponse(BaseModel):
    """Successful login: session token + profile."""

    token: str
    expires_at: datetime
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=8, max_length=200)

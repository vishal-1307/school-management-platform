"""Auth-related schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class TokenPayload(BaseModel):
    """Decoded JWT payload from Clerk."""

    sub: str
    email: str | None = None
    exp: int | None = None
    iat: int | None = None


class UserResponse(BaseModel):
    """Public user profile returned by /me."""

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


class LoginResponse(BaseModel):
    """Response returned after login verification."""

    user: UserResponse
    message: str = "Login successful"

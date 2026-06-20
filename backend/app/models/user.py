"""User model — linked to Clerk for authentication."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    """Platform roles enforced at the API level."""

    SUPER_ADMIN = "super_admin"
    OFFICE_ADMIN = "office_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class User(Base):
    """Application user synced from Clerk; stores role and optional entity links."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    clerk_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_constraint=True),
        nullable=False,
    )
    linked_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"))
    linked_student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"))
    linked_parent_id: Mapped[int | None] = mapped_column(ForeignKey("parents.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    permissions: Mapped[dict | None] = mapped_column(JSON, comment="Fine-grained overrides")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} clerk_id={self.clerk_id!r} role={self.role.value}>"

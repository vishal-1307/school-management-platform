"""User & role management endpoints (SRS §6.15) with audit trail.

Logins are institution-issued: the admin creates each account with a
login ID (admission number for students, employee ID for staff) and a
password. Passwords are bcrypt-hashed and never appear in audit logs.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.user import (
    AuditLogResponse,
    PasswordReset,
    UserAdminResponse,
    UserCreate,
    UserUpdate,
)
from app.services.security import hash_password

router = APIRouter(prefix="/users", tags=["Users & Roles"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


async def log_action(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Append a row to the audit trail. Never pass password material in detail."""
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )


@router.get("/audit-log", response_model=List[AuditLogResponse])
async def list_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> List[AuditLogResponse]:
    """Audit trail of admin actions, newest first."""
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [AuditLogResponse.model_validate(row) for row in result.scalars().all()]


@router.get("/", response_model=List[UserAdminResponse])
async def list_users(
    role: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[UserAdminResponse]:
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == UserRole(role))
    result = await db.execute(query)
    return [UserAdminResponse.model_validate(u) for u in result.scalars().all()]


@router.post("/", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> UserAdminResponse:
    """Create a login with an institution-issued ID and password."""
    login_id = payload.login_id.strip()
    existing = await db.execute(
        select(User).where(func.lower(User.login_id) == login_id.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Login ID '{login_id}' is already taken")

    user = User(
        login_id=login_id,
        password_hash=hash_password(payload.password),
        email=payload.email,
        phone=payload.phone,
        role=UserRole(payload.role),
        linked_staff_id=payload.linked_staff_id,
        linked_student_id=payload.linked_student_id,
        linked_parent_id=payload.linked_parent_id,
        permissions=payload.permissions,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await log_action(
        db,
        current_user,
        "user.create",
        "user",
        user.id,
        {"role": payload.role, "login_id": login_id},
    )
    await db.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> UserAdminResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field == "role":
            value = UserRole(value)
        setattr(user, field, value)

    if changes.get("is_active") is False:
        # Revoke outstanding sessions immediately.
        user.token_version += 1

    await log_action(db, current_user, "user.update", "user", user.id, changes)
    await db.flush()
    await db.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.post("/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Immediately revoke a user's access (SRS 6.15)."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")

    user.is_active = False
    user.token_version += 1  # kill any live sessions right now

    await log_action(db, current_user, "user.deactivate", "user", user.id)
    return MessageResponse(message="User deactivated")


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_password(
    user_id: int,
    payload: PasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Set a new password for any user (SRS 5.2, 6.15); revokes their sessions."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(payload.password)
    user.token_version += 1

    await log_action(db, current_user, "user.reset_password", "user", user.id)
    return MessageResponse(message="Password updated — share it with the user securely")

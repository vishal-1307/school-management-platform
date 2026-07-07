"""User & role management endpoints (SRS §6.15) with audit trail.

Creating a user provisions a matching Clerk account when CLERK_SECRET_KEY
is configured; otherwise the row is stored with a ``pending:`` clerk_id and
can be provisioned later via POST /users/{id}/provision.
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
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
from app.services import clerk as clerk_service

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
    """Append a row to the audit trail. Import and call from other routers too."""
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )


async def _provision_in_clerk(user: User, payload: UserCreate) -> str | None:
    """Create the Clerk account for a user; returns the clerk_id or None."""
    if not clerk_service.is_configured():
        return None
    try:
        clerk_user = await clerk_service.create_user(
            role=user.role.value,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            username=payload.username,
            password=payload.password,
        )
    except clerk_service.ClerkAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return clerk_user.get("id")


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
    """Create a login. Provisions a Clerk account when keys are configured."""
    user = User(
        clerk_id=f"pending:{uuid.uuid4()}",
        email=payload.email,
        phone=payload.phone,
        role=UserRole(payload.role),
        linked_staff_id=payload.linked_staff_id,
        linked_student_id=payload.linked_student_id,
        linked_parent_id=payload.linked_parent_id,
        permissions=payload.permissions,
        is_active=True,
    )
    clerk_id = await _provision_in_clerk(user, payload)
    if clerk_id:
        user.clerk_id = clerk_id

    db.add(user)
    await db.flush()
    await log_action(
        db,
        current_user,
        "user.create",
        "user",
        user.id,
        {"role": payload.role, "provisioned": bool(clerk_id)},
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

    # Mirror role/active changes into Clerk for real accounts.
    if clerk_service.is_configured() and not user.clerk_id.startswith("pending:"):
        try:
            if "role" in changes:
                await clerk_service.update_role(user.clerk_id, user.role.value)
            if changes.get("is_active") is False:
                await clerk_service.ban_user(user.clerk_id)
            elif changes.get("is_active") is True:
                await clerk_service.unban_user(user.clerk_id)
        except clerk_service.ClerkAPIError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

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
    if clerk_service.is_configured() and not user.clerk_id.startswith("pending:"):
        try:
            await clerk_service.ban_user(user.clerk_id)
        except clerk_service.ClerkAPIError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    await log_action(db, current_user, "user.deactivate", "user", user.id)
    return MessageResponse(message="User deactivated")


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_password(
    user_id: int,
    payload: PasswordReset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Set a new password for any user (SRS 5.2, 6.15)."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.clerk_id.startswith("pending:"):
        raise HTTPException(
            status_code=409,
            detail="User has no Clerk account yet — provision them first",
        )
    if not clerk_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk is not configured",
        )
    try:
        await clerk_service.set_password(user.clerk_id, payload.password)
    except clerk_service.ClerkAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    await log_action(db, current_user, "user.reset_password", "user", user.id)
    return MessageResponse(message="Password updated")


@router.post("/{user_id}/provision", response_model=UserAdminResponse)
async def provision_user(
    user_id: int,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> UserAdminResponse:
    """Create the Clerk account for a user stored while Clerk was unconfigured."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.clerk_id.startswith("pending:"):
        raise HTTPException(status_code=409, detail="User already has a Clerk account")
    if not clerk_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk is not configured",
        )

    clerk_id = await _provision_in_clerk(user, payload)
    user.clerk_id = clerk_id
    if payload.email:
        user.email = payload.email
    if payload.phone:
        user.phone = payload.phone

    await log_action(db, current_user, "user.provision", "user", user.id)
    await db.flush()
    await db.refresh(user)
    return UserAdminResponse.model_validate(user)

"""Authentication endpoints — institutional ID + password login.

Login is rate-limited two ways (per login ID and per client IP) because
institutional IDs are guessable (sequential admission numbers). Failure
responses are deliberately generic and timing-equalized so callers cannot
discover which IDs exist.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.staff import Staff
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, UserResponse
from app.schemas.common import MessageResponse
from app.services.ratelimit import LOGIN_ID_FAILURES, LOGIN_IP_ATTEMPTS, client_ip
from app.services.security import (
    DUMMY_HASH,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _build_user_response(db: AsyncSession, user: User) -> UserResponse:
    """Attach a display name and class/subject label from the linked record.

    Never touches email — this is an ID-only login system and no address
    should ever reach the frontend for the signed-in user's own profile.
    """
    response = UserResponse.model_validate(user)

    if user.linked_student_id:
        student = await db.get(
            Student, user.linked_student_id,
            options=[selectinload(Student.class_), selectinload(Student.section)],
        )
        if student:
            response.display_name = f"{student.first_name} {student.last_name}"
            class_name = student.class_.name if student.class_ else ""
            section_name = student.section.name if student.section else ""
            response.class_label = f"{class_name}-{section_name}" if class_name else None
    elif user.linked_staff_id:
        staff = await db.get(
            Staff, user.linked_staff_id,
            options=[selectinload(Staff.subject_assignments)],
        )
        if staff:
            response.display_name = f"{staff.first_name} {staff.last_name}"
            subject_names = sorted({
                a.subject.name for a in staff.subject_assignments if a.subject
            })
            response.class_label = ", ".join(subject_names) if subject_names else None
    else:
        # Admin/office-admin accounts have no linked person record.
        response.display_name = (
            "Super Admin" if user.role == UserRole.SUPER_ADMIN else "Office Admin"
        )

    return response

_BAD_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid ID or password",
)
_LOCKED_OUT = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many failed attempts — try again in 15 minutes",
)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Sign in with a school-issued login ID and password."""
    id_key = payload.login_id.strip().lower()
    ip_key = client_ip(request)

    if LOGIN_ID_FAILURES.is_blocked(id_key) or LOGIN_IP_ATTEMPTS.is_blocked(ip_key):
        raise _LOCKED_OUT
    LOGIN_IP_ATTEMPTS.record(ip_key)

    result = await db.execute(
        select(User).where(func.lower(User.login_id) == id_key)
    )
    user = result.scalar_one_or_none()

    # Always run a bcrypt verification so unknown IDs take the same time
    # as wrong passwords (no user enumeration via timing).
    password_ok = verify_password(
        payload.password, user.password_hash if user else DUMMY_HASH
    )

    if user is None or not password_ok or not user.is_active:
        LOGIN_ID_FAILURES.record(id_key)
        raise _BAD_CREDENTIALS

    LOGIN_ID_FAILURES.clear(id_key)
    token, expires_at = create_access_token(user.id, user.role.value, user.token_version)
    return LoginResponse(
        token=token,
        expires_at=expires_at,
        user=await _build_user_response(db, user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return await _build_user_response(db, current_user)


@router.post("/change-password", response_model=LoginResponse)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LoginResponse:
    """Change own password; revokes every other session and returns a fresh token."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version += 1
    await db.flush()

    token, expires_at = create_access_token(
        current_user.id, current_user.role.value, current_user.token_version
    )
    return LoginResponse(
        token=token,
        expires_at=expires_at,
        user=await _build_user_response(db, current_user),
    )


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Revoke every session for this account (all devices)."""
    current_user.token_version += 1
    await db.flush()
    return MessageResponse(message="Signed out everywhere — all sessions revoked")


@router.post("/logout", response_model=MessageResponse)
async def logout() -> MessageResponse:
    """Stateless logout — the client discards its token/cookie.

    Use /logout-all to revoke the token server-side as well.
    """
    return MessageResponse(message="Logged out")

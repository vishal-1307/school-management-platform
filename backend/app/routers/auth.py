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

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
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
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)


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
        user=UserResponse.model_validate(current_user),
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

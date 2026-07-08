"""Session verification and role-based access control.

``get_current_user`` verifies the platform's own HS256 session JWT from
the Authorization header and loads the local User row. ``require_role``
is a dependency factory that restricts endpoints to specific roles.

Tokens are revocable: each carries the user's ``token_version`` (``tv``
claim) at issue time; any mismatch with the current DB value — after a
password change/reset, deactivation, or logout-everywhere — rejects the
token immediately regardless of its expiry.
"""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.services.security import JWTError, decode_token

logger = logging.getLogger(__name__)

_INVALID_SESSION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired session — please sign in again",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _extract_token(request: Request) -> str:
    auth_header: str | None = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header.split(" ", 1)[1]


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: verify the session token and return the User.

    Raises:
        HTTPException 401: Missing/invalid/expired/revoked token.
        HTTPException 503: SECRET_KEY not configured on the server.
    """
    if not settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (SECRET_KEY is unset)",
        )

    token = await _extract_token(request)
    try:
        payload = decode_token(token)
    except JWTError as exc:
        logger.info("Rejected session token: %s", exc)
        raise _INVALID_SESSION

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise _INVALID_SESSION

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _INVALID_SESSION
    if payload.get("tv") != user.token_version:
        # Token predates a password change/reset or logout-everywhere.
        raise _INVALID_SESSION

    return user


def require_role(*roles: UserRole):
    """Dependency factory that enforces role-based access.

    Usage::

        @router.get("/admin-only")
        async def admin_view(user: User = Depends(require_role(UserRole.SUPER_ADMIN))):
            ...

    Raises:
        HTTPException 403: If the user's role is not in the allowed set.
    """

    async def _role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted. Required: {[r.value for r in roles]}",
            )
        return current_user

    return _role_checker

"""JWT verification and role-based access control middleware.

``get_current_user`` verifies the Clerk-issued JWT from the Authorization
header and loads the local User row.  ``require_role`` is a dependency
factory that restricts endpoints to specific roles.
"""

from __future__ import annotations

from typing import Sequence

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole


async def _extract_token(request: Request) -> str:
    """Pull the Bearer token from the Authorization header."""
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
    """FastAPI dependency: verify JWT and return the authenticated User.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
        HTTPException 401: If no matching user exists in the database.
    """
    token = await _extract_token(request)

    try:
        payload = jwt.decode(
            token,
            settings.clerk_secret_key,
            algorithms=["RS256", "HS256"],
            options={
                "verify_aud": False,
                "verify_iss": bool(settings.clerk_issuer),
            },
            issuer=settings.clerk_issuer or None,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clerk_id: str | None = payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim",
        )

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

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

"""JWT verification and role-based access control middleware.

``get_current_user`` verifies the Clerk-issued JWT from the Authorization
header and loads the local User row.  ``require_role`` is a dependency
factory that restricts endpoints to specific roles.

Clerk session tokens are RS256-signed; they are verified against Clerk's
JWKS (fetched from CLERK_JWKS_URL or derived from CLERK_ISSUER and cached).

Demo fallback: when no Clerk key is configured AND DEV_AUTH=true, tokens of
the form ``dev:<role>`` resolve to the first active seeded user of that
role. This exists only so the platform can be demoed before the Clerk app
is created — remove DEV_AUTH in production.
"""

from __future__ import annotations

import time

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

_JWKS_TTL_SECONDS = 3600
_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}


def _jwks_url() -> str:
    if settings.clerk_jwks_url:
        return settings.clerk_jwks_url
    if settings.clerk_issuer:
        return settings.clerk_issuer.rstrip("/") + "/.well-known/jwks.json"
    return ""


async def _fetch_jwks(force: bool = False) -> list[dict]:
    """Return Clerk's JWKS keys, cached for an hour."""
    now = time.time()
    if (
        not force
        and _jwks_cache["keys"]
        and now - _jwks_cache["fetched_at"] < _JWKS_TTL_SECONDS
    ):
        return _jwks_cache["keys"]

    url = _jwks_url()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (set CLERK_JWKS_URL or CLERK_ISSUER)",
        )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            keys = response.json().get("keys", [])
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch Clerk JWKS: {exc}",
        )
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


async def _signing_key_for(token: str) -> dict:
    """Find the JWK matching the token's key id, refetching once on rotation."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Malformed token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    kid = header.get("kid")
    for keys in (await _fetch_jwks(), await _fetch_jwks(force=True)):
        for key in keys:
            if key.get("kid") == kid:
                return key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token signing key not found in Clerk JWKS",
        headers={"WWW-Authenticate": "Bearer"},
    )


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


def _dev_auth_active() -> bool:
    return settings.dev_auth and not settings.clerk_secret_key


async def _resolve_dev_user(token: str, db: AsyncSession) -> User:
    """Resolve a ``dev:<role>`` token to the first active user of that role."""
    role_value = token.split(":", 1)[1]
    try:
        role = UserRole(role_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown dev role '{role_value}'. "
            f"Valid: {[r.value for r in UserRole]}",
        )
    result = await db.execute(
        select(User)
        .where(User.role == role, User.is_active)
        .order_by(User.id)
        .limit(1)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No active user with role '{role.value}' exists yet "
            "(run the seed script or create one as admin)",
        )
    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: verify JWT and return the authenticated User.

    Raises:
        HTTPException 401: If the token is missing, expired, or invalid.
        HTTPException 401: If no matching user exists in the database.
        HTTPException 503: If Clerk is not configured and DEV_AUTH is off.
    """
    token = await _extract_token(request)

    if token.startswith("dev:"):
        if not _dev_auth_active():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Dev tokens are disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await _resolve_dev_user(token, db)

    key = await _signing_key_for(token)
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
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

"""Authentication endpoints — login verification, current user, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginResponse, UserResponse
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    current_user: User = Depends(get_current_user),
) -> LoginResponse:
    """Verify the Clerk JWT and return the user profile.

    The actual authentication happens in Clerk on the frontend.  This
    endpoint simply validates the token, ensures the user exists in the
    local database, and returns their profile.
    """
    return LoginResponse(user=UserResponse.model_validate(current_user))


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout() -> MessageResponse:
    """Logout placeholder — actual token invalidation is handled by Clerk.

    This endpoint exists for frontend symmetry and can be extended to
    clear server-side sessions if needed in the future.
    """
    return MessageResponse(message="Logged out successfully")

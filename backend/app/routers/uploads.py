"""Cloudinary direct-upload signatures for portal file uploads.

The frontend uploads files straight to Cloudinary using a signature minted
here (gallery photos, homework attachments, submissions, student photos).
Returns 503 with a clear message while CLOUDINARY_URL is unset.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.services import cloudinary as cloudinary_service

router = APIRouter(prefix="/uploads", tags=["Uploads"])

UPLOADER_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.OFFICE_ADMIN,
    UserRole.TEACHER,
    UserRole.STUDENT,
)


@router.get("/signature")
async def upload_signature(
    folder: str = Query("general", max_length=50, pattern="^[a-z0-9_/-]+$"),
    current_user: User = Depends(require_role(*UPLOADER_ROLES)),
) -> dict:
    """Mint a signed direct-upload payload for the given folder."""
    if not settings.cloudinary_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File uploads are not configured yet (CLOUDINARY_URL is unset)",
        )
    # Students may only upload homework submissions.
    if current_user.role == UserRole.STUDENT and not folder.startswith("submissions"):
        raise HTTPException(status_code=403, detail="Students can only upload submissions")
    return cloudinary_service.generate_upload_signature(folder=folder)

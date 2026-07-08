"""Unauthenticated read endpoints for the public website.

The public site (notice board, ticker, faculty directory, school profile)
and the public contact form live here. Only fields safe for public display
are returned — no phone numbers or emails for staff, no internal notice
audiences.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.contact import ContactMessage
from app.models.notice import Notice, NoticeAudience
from app.models.school import School
from app.models.staff import Staff
from app.schemas.common import MessageResponse
from app.schemas.contact import ContactSubmit
from app.services.ratelimit import enforce_public_form_limit

router = APIRouter(prefix="/public", tags=["Public Website"])


class PublicNotice(BaseModel):
    id: int
    title: str
    content: str
    attachment_url: str | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class PublicFaculty(BaseModel):
    """Staff directory entry with public-safe fields only (no contacts)."""

    id: int
    first_name: str
    last_name: str
    photo_url: str | None = None
    qualification: str | None = None
    designation: str | None = None

    model_config = {"from_attributes": True}


class PublicSchool(BaseModel):
    name: str
    logo_url: str | None = None
    address: str | None = None
    affiliation_number: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None

    model_config = {"from_attributes": True}


@router.get("/notices", response_model=List[PublicNotice])
async def public_notices(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[PublicNotice]:
    """Published notices addressed to everyone (the public notice board)."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Notice)
        .where(
            Notice.audience == NoticeAudience.EVERYONE,
            Notice.published_at.is_not(None),
        )
        .order_by(Notice.published_at.desc())
        .limit(limit * 2)  # headroom for the channel filter below
    )
    notices = []
    for notice in result.scalars().all():
        published = notice.published_at
        if published is not None and published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published is not None and published > now:
            continue  # scheduled for the future
        channels = notice.channels or []
        if channels and "website" not in channels:
            continue
        notices.append(PublicNotice.model_validate(notice))
        if len(notices) >= limit:
            break
    return notices


@router.get("/faculty", response_model=List[PublicFaculty])
async def public_faculty(db: AsyncSession = Depends(get_db)) -> List[PublicFaculty]:
    """Active staff for the public faculty directory (SRS 4.2.5)."""
    result = await db.execute(
        select(Staff).where(Staff.is_active).order_by(Staff.id)
    )
    return [PublicFaculty.model_validate(s) for s in result.scalars().all()]


@router.get("/school", response_model=PublicSchool | None)
async def public_school(db: AsyncSession = Depends(get_db)) -> PublicSchool | None:
    """School profile for headers/footers/contact page."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    return PublicSchool.model_validate(school) if school else None


@router.post(
    "/contact",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_public_form_limit)],
)
async def submit_contact(
    payload: ContactSubmit,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Public Contact Us form → admin inbox (SRS 4.2.11). Rate-limited per IP."""
    db.add(ContactMessage(**payload.model_dump()))
    return MessageResponse(message="Thank you — the school office will get back to you soon.")

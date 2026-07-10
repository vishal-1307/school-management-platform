"""Admission enquiry endpoints — public submit and admin pipeline."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.admission import AdmissionEnquiry, EnquiryStatus
from app.models.user import User, UserRole
from app.schemas.admission import (
    EnquiryListResponse,
    EnquiryResponse,
    EnquirySubmit,
    EnquiryUpdate,
)
from app.schemas.common import MessageResponse
from app.services.ratelimit import enforce_public_form_limit

router = APIRouter(prefix="/admissions", tags=["Admissions"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


@router.post(
    "/enquiry",
    response_model=EnquiryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_public_form_limit)],
)
async def submit_enquiry(
    payload: EnquirySubmit,
    db: AsyncSession = Depends(get_db),
) -> EnquiryResponse:
    """Submit an admission enquiry (public, no auth required).

    This endpoint is exposed on the school website for prospective parents.
    Rate-limited per IP to curb spam.
    """
    enquiry = AdmissionEnquiry(**payload.model_dump())
    db.add(enquiry)
    await db.flush()
    await db.refresh(enquiry)
    return EnquiryResponse.model_validate(enquiry)


@router.get("/", response_model=EnquiryListResponse)
async def list_enquiries(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> EnquiryListResponse:
    """List all admission enquiries with optional status filter."""
    query = select(AdmissionEnquiry)
    count_query = select(func.count(AdmissionEnquiry.id))
    if status_filter:
        f = AdmissionEnquiry.status == EnquiryStatus(status_filter)
        query = query.where(f)
        count_query = count_query.where(f)

    total = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total / page_size) if total else 0

    query = query.order_by(AdmissionEnquiry.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    return EnquiryListResponse(
        items=[EnquiryResponse.model_validate(e) for e in result.scalars().all()],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{enquiry_id}", response_model=EnquiryResponse)
async def get_enquiry(
    enquiry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> EnquiryResponse:
    """Get a single enquiry by ID."""
    result = await db.execute(
        select(AdmissionEnquiry).where(AdmissionEnquiry.id == enquiry_id),
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return EnquiryResponse.model_validate(enquiry)


@router.put("/{enquiry_id}", response_model=EnquiryResponse)
async def update_enquiry(
    enquiry_id: int,
    payload: EnquiryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> EnquiryResponse:
    """Move an enquiry through the admission pipeline."""
    result = await db.execute(
        select(AdmissionEnquiry).where(AdmissionEnquiry.id == enquiry_id),
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.status = EnquiryStatus(payload.status)
    if payload.notes is not None:
        enquiry.notes = payload.notes

    await db.flush()
    await db.refresh(enquiry)
    return EnquiryResponse.model_validate(enquiry)


@router.delete("/{enquiry_id}", response_model=MessageResponse)
async def delete_enquiry(
    enquiry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Delete an admission enquiry."""
    result = await db.execute(
        select(AdmissionEnquiry).where(AdmissionEnquiry.id == enquiry_id),
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    await db.delete(enquiry)
    await db.flush()
    return MessageResponse(message="Enquiry deleted")

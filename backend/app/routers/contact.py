"""Admin inbox for public contact-form submissions (SRS §4.2.11)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.contact import ContactMessage
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.contact import ContactMessageResponse

router = APIRouter(prefix="/contact-messages", tags=["Contact Messages"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


@router.get("/", response_model=List[ContactMessageResponse])
async def list_messages(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[ContactMessageResponse]:
    query = select(ContactMessage).order_by(ContactMessage.created_at.desc())
    if unread_only:
        query = query.where(ContactMessage.is_read.is_(False))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return [ContactMessageResponse.model_validate(m) for m in result.scalars().all()]


@router.put("/{message_id}/read", response_model=ContactMessageResponse)
async def mark_read(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> ContactMessageResponse:
    message = await db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_read = True
    await db.flush()
    await db.refresh(message)
    return ContactMessageResponse.model_validate(message)


@router.delete("/{message_id}", response_model=MessageResponse)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    message = await db.get(ContactMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.delete(message)
    return MessageResponse(message="Message deleted")

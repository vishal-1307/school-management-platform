"""Communication log — searchable WhatsApp message history (SRS §6.13)."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.communication import DeliveryStatus, WhatsAppMessageLog
from app.models.user import User, UserRole

router = APIRouter(prefix="/communication", tags=["Communication Log"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


class MessageLogResponse(BaseModel):
    id: int
    recipient_phone: str
    message_type: str
    content_summary: str | None = None
    template_name: str | None = None
    delivery_status: str
    sent_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[MessageLogResponse])
async def list_messages(
    phone: str | None = Query(None),
    delivery_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[MessageLogResponse]:
    """WhatsApp message log, newest first, filterable by phone/status."""
    query = select(WhatsAppMessageLog)
    if phone:
        query = query.where(WhatsAppMessageLog.recipient_phone.ilike(f"%{phone}%"))
    if delivery_status:
        query = query.where(
            WhatsAppMessageLog.delivery_status == DeliveryStatus(delivery_status)
        )
    query = (
        query.order_by(WhatsAppMessageLog.sent_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return [MessageLogResponse.model_validate(m) for m in result.scalars().all()]

"""Notice endpoints — compose, list, schedule."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.notice import Notice, NoticeAudience
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.notice import NoticeCreate, NoticeResponse

router = APIRouter(prefix="/notices", tags=["Notices"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


@router.post("/", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
async def compose_notice(
    payload: NoticeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES, UserRole.TEACHER)),
) -> NoticeResponse:
    """Compose and optionally schedule a notice.

    If ``scheduled_at`` is provided, the notice will be published at that
    time. Otherwise it is published immediately.
    """
    published_at = None if payload.scheduled_at else datetime.utcnow()

    notice = Notice(
        title=payload.title,
        content=payload.content,
        attachment_url=payload.attachment_url,
        audience=NoticeAudience(payload.audience),
        target_class_id=payload.target_class_id,
        channels=payload.channels,
        scheduled_at=payload.scheduled_at,
        published_at=published_at,
        created_by_id=current_user.id,
    )
    db.add(notice)
    await db.flush()
    await db.refresh(notice)
    return NoticeResponse.model_validate(notice)


@router.get("/", response_model=List[NoticeResponse])
async def list_notices(
    audience: str | None = Query(None, pattern="^(everyone|class|staff)$"),
    class_id: int | None = Query(None),
    published_only: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER,
        UserRole.STUDENT, UserRole.PARENT,
    )),
) -> List[NoticeResponse]:
    """List notices with optional filters and pagination."""
    query = select(Notice)

    if audience:
        query = query.where(Notice.audience == NoticeAudience(audience))
    if class_id:
        query = query.where(Notice.target_class_id == class_id)
    if published_only:
        query = query.where(Notice.published_at.isnot(None))

    query = query.order_by(Notice.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return [NoticeResponse.model_validate(n) for n in result.scalars().all()]


@router.post("/{notice_id}/broadcast", response_model=MessageResponse)
async def broadcast_notice_now(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Send this notice to all targeted parents on WhatsApp (FR-20/21)."""
    notice = await db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found")

    from app.services.automations import broadcast_notice

    sent = await broadcast_notice(notice_id)
    if sent == -1:
        raise HTTPException(
            status_code=409,
            detail="Notice broadcasts are switched off — enable them in Settings → Automation",
        )
    return MessageResponse(
        message=f"Broadcast queued to {sent} parents (see Communication Log for delivery status)"
    )


@router.get("/{notice_id}", response_model=NoticeResponse)
async def get_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER,
        UserRole.STUDENT, UserRole.PARENT,
    )),
) -> NoticeResponse:
    """Get a single notice by ID."""
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")
    return NoticeResponse.model_validate(notice)


@router.delete("/{notice_id}", response_model=MessageResponse)
async def delete_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Delete a notice."""
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice not found")

    await db.delete(notice)
    await db.flush()
    return MessageResponse(message="Notice deleted")

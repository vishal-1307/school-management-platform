"""Inbound webhooks (Clerk user lifecycle events).

Keeps local User rows in sync when accounts are edited or removed in the
Clerk dashboard. Signature-verified (Svix); no session auth by design.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services import clerk as clerk_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    body = await request.body()
    if not clerk_service.verify_webhook(dict(request.headers), body):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    event = json.loads(body)
    event_type = event.get("type", "")
    data = event.get("data", {})
    clerk_id = data.get("id")
    if not clerk_id:
        return {"received": True}

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is None:
        return {"received": True, "matched": False}

    if event_type == "user.updated":
        emails = data.get("email_addresses") or []
        if emails:
            user.email = emails[0].get("email_address") or user.email
        phones = data.get("phone_numbers") or []
        if phones:
            user.phone = phones[0].get("phone_number") or user.phone
        if data.get("banned") is True:
            user.is_active = False
    elif event_type == "user.deleted":
        user.is_active = False

    return {"received": True, "matched": True}

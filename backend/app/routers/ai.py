"""AI assistant endpoints — role-scoped chat with confirm-before-write.

One shared endpoint set; the toolset is selected server-side from the
authenticated user's role (see ``services/ai/tools.py``). Gated by the
school-wide ``ai_assistant_enabled`` feature flag and rate-limited per user.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.school import School
from app.models.user import User
from app.schemas.ai import (
    CancelRequest,
    ChatRequest,
    ChatResponse,
    ConfirmRequest,
    ConfirmResponse,
)
from app.schemas.common import MessageResponse
from app.services.ai.assistant import cancel_pending_action, confirm_pending_action, run_assistant
from app.services.ai.client import AIUnavailable
from app.services.ratelimit import SlidingWindowLimiter

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

# 20 requests/minute/user — generous for a chat UI, cheap to abuse otherwise.
AI_CHAT_LIMITER = SlidingWindowLimiter(max_events=20, window_seconds=60)


async def _require_feature_enabled(db: AsyncSession) -> None:
    result = await db.execute(select(School))
    school = result.scalars().first()
    enabled = (
        bool((school.settings or {}).get("features", {}).get("ai_assistant_enabled", False))
        if school else False
    )
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The AI assistant is not enabled for this school.",
        )


def _enforce_rate_limit(current_user: User) -> None:
    if not AI_CHAT_LIMITER.check_and_record(str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests to the assistant — please wait a moment.",
        )


@router.post("/assistant/chat", response_model=ChatResponse)
async def assistant_chat(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """One chat turn. Read tools run immediately; a ready write only stages a pending_action."""
    await _require_feature_enabled(db)
    _enforce_rate_limit(current_user)
    try:
        result = await run_assistant(
            db, current_user, [t.model_dump() for t in payload.transcript], background_tasks,
        )
    except AIUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is temporarily unavailable — please try again shortly.",
        )
    return ChatResponse(**result)


@router.post("/assistant/confirm", response_model=ConfirmResponse)
async def assistant_confirm(
    payload: ConfirmRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConfirmResponse:
    """Execute a previously staged write. Re-validates ownership and expiry server-side."""
    await _require_feature_enabled(db)
    _enforce_rate_limit(current_user)
    reply = await confirm_pending_action(db, current_user, payload.action_id, background_tasks)
    if reply is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That action has expired or was already handled.",
        )
    return ConfirmResponse(reply=reply)


@router.post("/assistant/cancel", response_model=MessageResponse)
async def assistant_cancel(
    payload: CancelRequest,
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Drop a staged write; harmless no-op if it's already gone."""
    cancel_pending_action(current_user, payload.action_id)
    return MessageResponse(message="Cancelled.")

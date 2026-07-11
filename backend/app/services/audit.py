"""Shared audit-trail helper (SRS §6.15).

Lifted out of ``routers/users.py`` so both the ordinary admin endpoints and
the AI assistant layer write to the exact same trail through the exact same
function — never pass password material in ``detail``.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


async def log_action(
    db: AsyncSession,
    user: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Append a row to the audit trail. Never pass password material in detail."""
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )

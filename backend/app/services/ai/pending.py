"""In-memory TTL store for pending (unconfirmed) AI write actions.

Phase 1 of the confirm-before-write flow (the chat turn) never mutates —
it only resolves a WRITE tool's arguments and stores them here, keyed by a
random ``action_id`` bound to the requesting user. Phase 2 (``/confirm``)
looks the action up, checks ownership + expiry, and executes it. The
client never holds or re-sends the executable arguments, so it cannot
tamper with what gets run.

Process-local state, same trade-off as ``services/ratelimit.py`` — fine on
Render's single free instance.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.models.user import UserRole

_TTL_SECONDS = 300


@dataclass
class PendingAction:
    action_id: str
    user_id: int
    tool_name: str
    args: dict[str, Any]
    title: str
    summary: str
    preview: Any
    executor: Callable[..., Any]
    expires_at: float
    # Roles allowed to run this tool, captured at proposal time. Re-checked
    # against current_user.role at /confirm — a role change between propose
    # and confirm must not grant a privilege the current role lacks.
    required_roles: tuple[UserRole, ...] = field(default_factory=tuple)


_STORE: dict[str, PendingAction] = {}


def _prune() -> None:
    now = time.monotonic()
    expired = [key for key, action in _STORE.items() if action.expires_at < now]
    for key in expired:
        del _STORE[key]


def create(
    user_id: int,
    tool_name: str,
    args: dict[str, Any],
    title: str,
    summary: str,
    preview: Any,
    executor: Callable[..., Any],
    required_roles: tuple[UserRole, ...] = (),
) -> PendingAction:
    _prune()
    action_id = secrets.token_urlsafe(16)
    action = PendingAction(
        action_id=action_id,
        user_id=user_id,
        tool_name=tool_name,
        args=args,
        title=title,
        summary=summary,
        preview=preview,
        executor=executor,
        expires_at=time.monotonic() + _TTL_SECONDS,
        required_roles=required_roles,
    )
    _STORE[action_id] = action
    return action


def get(action_id: str, user_id: int) -> PendingAction | None:
    """Return the action only if it exists, isn't expired, and belongs to user_id."""
    _prune()
    action = _STORE.get(action_id)
    if action is None or action.user_id != user_id:
        return None
    return action


def discard(action_id: str) -> None:
    _STORE.pop(action_id, None)

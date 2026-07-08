"""In-memory sliding-window rate limiting.

Protects the login endpoint (guessable institutional IDs) and the public
website forms (spam). State is per-process — fine on Render's single free
instance; swap for Redis if the service ever scales horizontally.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    """Counts events per key within a rolling time window."""

    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: Dict[str, Deque[float]] = {}

    def _prune(self, key: str) -> Deque[float] | None:
        events = self._events.get(key)
        if events is None:
            return None
        cutoff = time.monotonic() - self.window_seconds
        while events and events[0] < cutoff:
            events.popleft()
        if not events:
            # Don't let the dict grow unboundedly with dead keys.
            del self._events[key]
            return None
        return events

    def is_blocked(self, key: str) -> bool:
        events = self._prune(key)
        return events is not None and len(events) >= self.max_events

    def record(self, key: str) -> None:
        self._prune(key)
        self._events.setdefault(key, deque()).append(time.monotonic())

    def clear(self, key: str) -> None:
        self._events.pop(key, None)

    def check_and_record(self, key: str) -> bool:
        """Record one event; returns False if the key is over its limit."""
        if self.is_blocked(key):
            return False
        self.record(key)
        return True


# Login: lock a login ID after 5 failures in 15 minutes; cap any single IP
# at 20 attempts (success or failure) per 15 minutes.
LOGIN_ID_FAILURES = SlidingWindowLimiter(max_events=5, window_seconds=900)
LOGIN_IP_ATTEMPTS = SlidingWindowLimiter(max_events=20, window_seconds=900)

# Public website forms (admission enquiry, contact): 5 posts/min/IP.
PUBLIC_FORM_LIMITER = SlidingWindowLimiter(max_events=5, window_seconds=60)


def client_ip(request: Request) -> str:
    """Best-effort client IP behind Render's proxy."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_public_form_limit(request: Request) -> None:
    """FastAPI dependency for unauthenticated form POSTs."""
    if not PUBLIC_FORM_LIMITER.check_and_record(client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions — please wait a minute and try again.",
        )

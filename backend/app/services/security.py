"""Password hashing and session-token issuing for institutional auth.

bcrypt for password storage (per-hash random salt built in) and HS256 JWTs
signed with SECRET_KEY for sessions. Tokens carry the user's
``token_version`` so bumping it server-side revokes every outstanding
session instantly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# Verified against when a login ID doesn't exist, so unknown-ID and
# wrong-password attempts take the same time (prevents user enumeration).
DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()

# Sentinel written by the migration for pre-existing rows; can never match
# any password because it is not a valid bcrypt hash.
UNUSABLE_HASH = "!"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode())
    except ValueError:
        # Malformed/unusable hash (e.g. the migration sentinel "!")
        return False


def create_access_token(user_id: int, role: str, token_version: int) -> tuple[str, datetime]:
    """Return (token, expires_at) for a successful login."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.access_token_hours)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, expires_at


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a session token. Raises JWTError on any problem."""
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


__all__ = [
    "DUMMY_HASH",
    "UNUSABLE_HASH",
    "JWTError",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
]

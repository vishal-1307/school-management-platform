"""Application-wide configuration loaded from environment variables.

Uses pydantic-settings so every secret is validated at startup and never
hard-coded in source control.
"""

import json
from typing import Annotated, List, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def normalize_database_url(url: str) -> Tuple[str, bool]:
    """Normalize a Postgres URL for asyncpg and extract SSL intent.

    Returns (url, ssl_required).

    Handles the two things managed-Postgres providers (Neon, Render, Heroku)
    put in their connection strings that break SQLAlchemy+asyncpg:
    - ``postgres://`` / ``postgresql://`` schemes → ``postgresql+asyncpg://``
    - ``?sslmode=require&channel_binding=require`` query params — asyncpg
      does not accept either keyword, so they are stripped here and the SSL
      requirement is applied via ``connect_args`` in ``app.database`` instead.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    ssl_required = False
    if url.startswith("postgresql+asyncpg://"):
        parts = urlsplit(url)
        kept_params = []
        for key, value in parse_qsl(parts.query):
            if key == "sslmode":
                ssl_required = value != "disable"
                continue
            if key == "channel_binding":
                continue
            kept_params.append((key, value))
        url = urlunsplit(parts._replace(query=urlencode(kept_params)))
    return url, ssl_required


class Settings(BaseSettings):
    """Central configuration sourced from ``.env`` or real env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./school.db"
    database_ssl_required: bool = False

    def __init__(self, **values):
        super().__init__(**values)
        self.database_url, ssl_required = normalize_database_url(self.database_url)
        if ssl_required:
            self.database_ssl_required = True

    # ── Auth (institutional ID + password) ─────────────────────────────
    # SECRET_KEY signs the session JWTs. Must be a long random value in
    # production (render.yaml generates one); auth returns 503 if unset.
    secret_key: str = ""
    # Session lifetime; tokens also die early when the user's token_version
    # is bumped (password change/reset, deactivation, logout-everywhere).
    access_token_hours: int = 24

    # ── Bootstrap switches ──────────────────────────────────────────────
    # SEED_ON_START: run the idempotent demo seed at boot.
    seed_on_start: bool = False

    # ── Razorpay ────────────────────────────────────────────────────────
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ── Cloudinary ──────────────────────────────────────────────────────
    cloudinary_url: str = ""

    # ── WhatsApp Cloud API ──────────────────────────────────────────────
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    # ── Frontend ────────────────────────────────────────────────────────
    frontend_url: str = ""

    # ── CORS ────────────────────────────────────────────────────────────
    # Accepts either a JSON array or a plain comma-separated string, so a
    # value like "https://site.vercel.app" set in a dashboard cannot crash
    # Settings() at import time (pydantic-settings default requires JSON).
    cors_origins: Annotated[List[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4321",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()

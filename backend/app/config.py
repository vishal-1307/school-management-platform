"""Application-wide configuration loaded from environment variables.

Uses pydantic-settings so every secret is validated at startup and never
hard-coded in source control.
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration sourced from ``.env`` or real env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./school.db"


    # ── Clerk Auth ──────────────────────────────────────────────────────
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""

    # ── Razorpay ────────────────────────────────────────────────────────
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # ── Cloudinary ──────────────────────────────────────────────────────
    cloudinary_url: str = ""

    # ── WhatsApp Cloud API ──────────────────────────────────────────────
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    # ── CORS ────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]


settings = Settings()

"""Cloudinary upload and URL helpers."""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict
from urllib.parse import urlparse

from app.config import settings


def _parse_cloudinary_url() -> tuple[str, str, str]:
    """Parse CLOUDINARY_URL into (cloud_name, api_key, api_secret)."""
    parsed = urlparse(settings.cloudinary_url)
    api_key = parsed.username or ""
    api_secret = parsed.password or ""
    cloud_name = parsed.hostname or ""
    return cloud_name, api_key, api_secret


async def generate_upload_signature(
    folder: str = "school",
    tags: str = "",
) -> Dict[str, Any]:
    """Generate a signed upload payload for client-side direct uploads.

    Returns:
        Dict with ``signature``, ``timestamp``, ``api_key``, ``cloud_name``,
        ``folder``, ``tags`` — everything the frontend needs.
    """
    cloud_name, api_key, api_secret = _parse_cloudinary_url()
    timestamp = int(time.time())

    params_to_sign = f"folder={folder}&tags={tags}&timestamp={timestamp}"
    signature = hashlib.sha1(
        f"{params_to_sign}{api_secret}".encode()
    ).hexdigest()

    return {
        "signature": signature,
        "timestamp": timestamp,
        "api_key": api_key,
        "cloud_name": cloud_name,
        "folder": folder,
        "tags": tags,
    }


async def get_optimized_url(
    public_id: str,
    width: int = 800,
    quality: str = "auto",
    format_: str = "auto",
) -> str:
    """Build a Cloudinary delivery URL with on-the-fly transformations.

    Args:
        public_id: The Cloudinary public ID of the asset.
        width: Target width in pixels.
        quality: Quality setting (``auto`` lets Cloudinary optimise).
        format_: Output format (``auto`` for best browser format).

    Returns:
        Fully qualified Cloudinary URL.
    """
    cloud_name, _, _ = _parse_cloudinary_url()
    transforms = f"w_{width},q_{quality},f_{format_}"
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{transforms}/{public_id}"

"""Clerk Backend API client and webhook verification.

Used to provision logins when the admin creates staff/student records, keep
role metadata in sync, and manage credentials (SRS §6.15). Every function
raises ``ClerkNotConfigured`` when CLERK_SECRET_KEY is unset so callers can
degrade gracefully (users are stored locally with a ``pending:`` clerk_id
and provisioned later).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any, Dict

import httpx

from app.config import settings

API_BASE = "https://api.clerk.com/v1"


class ClerkNotConfigured(RuntimeError):
    """Raised when Clerk credentials are not set in the environment."""


class ClerkAPIError(RuntimeError):
    """Raised when the Clerk Backend API returns an error response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        super().__init__(f"Clerk API error {status_code}: {detail}")


def is_configured() -> bool:
    return bool(settings.clerk_secret_key)


async def _request(method: str, path: str, json: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not is_configured():
        raise ClerkNotConfigured("CLERK_SECRET_KEY is not set")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.request(
            method,
            f"{API_BASE}{path}",
            json=json,
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        )
    if response.status_code >= 400:
        try:
            detail = response.json().get("errors", [{}])[0].get("message", response.text)
        except Exception:
            detail = response.text
        raise ClerkAPIError(response.status_code, detail)
    return response.json() if response.text else {}


async def create_user(
    *,
    role: str,
    first_name: str = "",
    last_name: str = "",
    email: str | None = None,
    phone: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> Dict[str, Any]:
    """Create a Clerk user with the platform role in public_metadata.

    Students typically get username+password (admission number as username,
    no email required); staff get email+password.
    """
    payload: Dict[str, Any] = {"public_metadata": {"role": role}}
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name
    if email:
        payload["email_address"] = [email]
    if phone:
        payload["phone_number"] = [phone]
    if username:
        payload["username"] = username
    if password:
        payload["password"] = password
        payload["skip_password_checks"] = True
    return await _request("POST", "/users", json=payload)


async def update_role(clerk_id: str, role: str) -> Dict[str, Any]:
    """Mirror the platform role into Clerk public_metadata."""
    return await _request(
        "PATCH", f"/users/{clerk_id}/metadata", json={"public_metadata": {"role": role}}
    )


async def set_password(clerk_id: str, password: str) -> Dict[str, Any]:
    return await _request(
        "PATCH",
        f"/users/{clerk_id}",
        json={"password": password, "skip_password_checks": True},
    )


async def ban_user(clerk_id: str) -> Dict[str, Any]:
    """Block sign-in for a deactivated user."""
    return await _request("POST", f"/users/{clerk_id}/ban")


async def unban_user(clerk_id: str) -> Dict[str, Any]:
    return await _request("POST", f"/users/{clerk_id}/unban")


async def delete_user(clerk_id: str) -> Dict[str, Any]:
    return await _request("DELETE", f"/users/{clerk_id}")


def verify_webhook(headers: Dict[str, str], body: bytes) -> bool:
    """Verify a Clerk (Svix) webhook signature.

    Svix signs ``{id}.{timestamp}.{body}`` with HMAC-SHA256 using the
    base64 part of the ``whsec_...`` secret; the header carries one or more
    space-separated ``v1,<base64sig>`` entries.
    """
    secret = settings.clerk_webhook_secret
    if not secret:
        return False
    svix_id = headers.get("svix-id", "")
    svix_timestamp = headers.get("svix-timestamp", "")
    svix_signature = headers.get("svix-signature", "")
    if not (svix_id and svix_timestamp and svix_signature):
        return False

    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed_content = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
    ).decode()

    for candidate in svix_signature.split(" "):
        version, _, signature = candidate.partition(",")
        if version == "v1" and hmac.compare_digest(expected, signature):
            return True
    return False

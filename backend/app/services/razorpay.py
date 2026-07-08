"""Razorpay payment service — order creation, signature verification, webhooks."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Any, Dict

import razorpay

from app.config import settings


class RazorpayNotConfigured(RuntimeError):
    """Raised when Razorpay credentials are not set in the environment."""


def is_configured() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


def _get_client() -> razorpay.Client:
    """Create a new Razorpay client from env credentials."""
    if not is_configured():
        raise RazorpayNotConfigured("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not set")
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


async def create_order(amount_paise: int, receipt: str, notes: Dict[str, str] | None = None) -> Dict[str, Any]:
    """Create a Razorpay order.

    Args:
        amount_paise: Amount in paise (e.g. 50000 = ₹500).
        receipt: Unique receipt identifier.
        notes: Optional key-value metadata.

    Returns:
        Razorpay order dict with ``id``, ``amount``, ``currency`` etc.

    Raises:
        RazorpayNotConfigured: If credentials are missing.
    """
    client = _get_client()
    order_data: Dict[str, Any] = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
    }
    if notes:
        order_data["notes"] = notes
    # The Razorpay SDK is synchronous; run it off the event loop.
    return await asyncio.to_thread(client.order.create, data=order_data)


async def verify_payment_signature(
    order_id: str,
    payment_id: str,
    signature: str,
) -> bool:
    """Verify the Razorpay payment signature to confirm authenticity.

    Returns:
        True if signature matches, False otherwise.
    """
    message = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_webhook(raw_body: bytes, signature: str) -> Dict[str, Any] | None:
    """Validate a Razorpay webhook and return the parsed event.

    Args:
        raw_body: The exact request body bytes as received (the HMAC must
            be computed over these, not a re-serialization — re-dumping
            the parsed JSON can differ from Razorpay's byte-for-byte
            payload in key order, unicode escaping, or whitespace, which
            would make correct payloads fail verification).
        signature: ``X-Razorpay-Signature`` header value.

    Returns:
        Parsed event dict if valid, None if signature mismatch.
    """
    import json

    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return None

    return json.loads(raw_body)

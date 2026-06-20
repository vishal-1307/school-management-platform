"""Razorpay payment service — order creation, signature verification, webhooks."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict

import razorpay

from app.config import settings


def _get_client() -> razorpay.Client:
    """Create a new Razorpay client from env credentials."""
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


async def create_order(amount_paise: int, receipt: str, notes: Dict[str, str] | None = None) -> Dict[str, Any]:
    """Create a Razorpay order.

    Args:
        amount_paise: Amount in paise (e.g. 50000 = ₹500).
        receipt: Unique receipt identifier.
        notes: Optional key-value metadata.

    Returns:
        Razorpay order dict with ``id``, ``amount``, ``currency`` etc.
    """
    client = _get_client()
    order_data: Dict[str, Any] = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
    }
    if notes:
        order_data["notes"] = notes
    return client.order.create(data=order_data)


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


async def process_webhook(payload: Dict[str, Any], signature: str) -> Dict[str, Any] | None:
    """Validate and extract a Razorpay webhook event.

    Args:
        payload: Raw JSON body from the webhook request.
        signature: ``X-Razorpay-Signature`` header value.

    Returns:
        Parsed event dict if valid, None if signature mismatch.
    """
    import json

    body = json.dumps(payload, separators=(",", ":"))
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return None

    return payload

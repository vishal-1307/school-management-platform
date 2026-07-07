"""WhatsApp Cloud API messaging service."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.communication import DeliveryStatus, WhatsAppMessageLog

logger = logging.getLogger(__name__)

_BASE_URL = "https://graph.facebook.com/v18.0"


def is_configured() -> bool:
    return bool(settings.whatsapp_token and settings.whatsapp_phone_id)


async def send_template_message(
    db: AsyncSession,
    to: str,
    template_name: str,
    language_code: str = "en",
    components: List[Dict[str, Any]] | None = None,
) -> bool:
    """Send a pre-approved WhatsApp template message.

    Args:
        db: Async database session for logging.
        to: Recipient phone number with country code.
        template_name: Name of the approved template.
        language_code: ISO language code.
        components: Optional template parameters.

    Returns:
        True if the API accepted the message, False on failure.
    """
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components

    if not is_configured():
        # Log what WOULD have been sent so the school sees the automation
        # working before WhatsApp credentials are configured.
        await _log_message(
            db, to, "template", f"Template: {template_name}", template_name, DeliveryStatus.SKIPPED
        )
        return False

    success = await _send(payload)
    status = DeliveryStatus.SENT if success else DeliveryStatus.FAILED
    await _log_message(db, to, "template", f"Template: {template_name}", template_name, status)
    return success


async def send_text_message(
    db: AsyncSession,
    to: str,
    body: str,
) -> bool:
    """Send a plain-text WhatsApp message.

    Args:
        db: Async database session for logging.
        to: Recipient phone number with country code.
        body: Text content to send.

    Returns:
        True if the API accepted the message, False on failure.
    """
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    if not is_configured():
        await _log_message(db, to, "text", body[:200], None, DeliveryStatus.SKIPPED)
        return False

    success = await _send(payload)
    status = DeliveryStatus.SENT if success else DeliveryStatus.FAILED
    await _log_message(db, to, "text", body[:200], None, status)
    return success


async def _send(payload: Dict[str, Any]) -> bool:
    """Execute the HTTP request to WhatsApp Cloud API."""
    url = f"{_BASE_URL}/{settings.whatsapp_phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return True
            logger.error("WhatsApp API error %s: %s", response.status_code, response.text)
            return False
    except httpx.HTTPError as exc:
        logger.error("WhatsApp HTTP error: %s", exc)
        return False


async def _log_message(
    db: AsyncSession,
    recipient_phone: str,
    message_type: str,
    content_summary: str | None,
    template_name: str | None,
    delivery_status: DeliveryStatus,
) -> None:
    """Persist a message log entry to the database."""
    log = WhatsAppMessageLog(
        recipient_phone=recipient_phone,
        message_type=message_type,
        content_summary=content_summary,
        template_name=template_name,
        delivery_status=delivery_status,
    )
    db.add(log)
    await db.flush()

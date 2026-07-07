"""WhatsApp message logging model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeliveryStatus(str, enum.Enum):
    """Delivery lifecycle states for a WhatsApp message."""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    # Automation ran but WhatsApp credentials are not configured — the
    # message is logged so the school sees what WOULD have been sent.
    SKIPPED = "skipped"


class WhatsAppMessageLog(Base):
    """Audit log for every WhatsApp message dispatched by the platform."""

    __tablename__ = "whatsapp_message_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="template/text/media")
    content_summary: Mapped[str | None] = mapped_column(Text)
    template_name: Mapped[str | None] = mapped_column(String(100))
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", create_constraint=True),
        default=DeliveryStatus.QUEUED,
        server_default="queued",
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WhatsAppMessageLog id={self.id} to={self.recipient_phone!r}>"

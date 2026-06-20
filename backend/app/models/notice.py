"""Notice / circular model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NoticeAudience(str, enum.Enum):
    """Who a notice targets."""

    EVERYONE = "everyone"
    CLASS = "class"
    STAFF = "staff"


class Notice(Base):
    """School notice / circular that can be sent via multiple channels."""

    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(512))
    audience: Mapped[NoticeAudience] = mapped_column(
        Enum(NoticeAudience, name="notice_audience", create_constraint=True),
        nullable=False,
        default=NoticeAudience.EVERYONE,
    )
    target_class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"))
    channels: Mapped[list | None] = mapped_column(
        JSON, default=list, comment='e.g. ["app","whatsapp","sms"]',
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    # relationships
    target_class: Mapped["Class | None"] = relationship(lazy="selectin")  # noqa: F821
    created_by: Mapped["User | None"] = relationship(lazy="selectin")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Notice id={self.id} title={self.title!r}>"

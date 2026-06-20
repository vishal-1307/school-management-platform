"""Admission enquiry model."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnquiryStatus(str, enum.Enum):
    """Pipeline stages for an admission enquiry."""

    NEW = "new"
    CONTACTED = "contacted"
    VISITED = "visited"
    ADMITTED = "admitted"
    NOT_INTERESTED = "not_interested"


class AdmissionEnquiry(Base):
    """Public-facing admission enquiry submitted by a prospective parent."""

    __tablename__ = "admission_enquiries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    child_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date)
    class_applying: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(50), comment="website/referral/walk-in")
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EnquiryStatus] = mapped_column(
        Enum(EnquiryStatus, name="enquiry_status", create_constraint=True),
        default=EnquiryStatus.NEW,
        server_default="new",
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, comment="Internal admin notes")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AdmissionEnquiry id={self.id} child={self.child_name!r}>"

"""Staff leave applications (SRS §7.8)."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LeaveApplication(Base):
    """A staff member's leave request awaiting admin review."""

    __tablename__ = "leave_applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus, name="leave_status", create_constraint=True),
        default=LeaveStatus.PENDING,
        server_default="pending",
        nullable=False,
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    staff = relationship("Staff", lazy="selectin")

    def __repr__(self) -> str:
        return f"<LeaveApplication id={self.id} staff={self.staff_id} status={self.status.value}>"

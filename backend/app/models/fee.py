"""Fee structure and transaction models."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentMode(str, enum.Enum):
    """Accepted payment modes."""

    CASH = "cash"
    CHEQUE = "cheque"
    ONLINE = "online"


class FeeStructure(Base):
    """Fee definition for a class in an academic year."""

    __tablename__ = "fee_structures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False, index=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), nullable=False, index=True)
    fee_head: Mapped[str] = mapped_column(String(100), nullable=False, comment="e.g. Tuition, Transport")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    term: Mapped[str | None] = mapped_column(String(30), comment="Q1, H1, Annual")

    # relationships
    academic_year: Mapped["AcademicYear"] = relationship(back_populates="fee_structures")  # noqa: F821
    class_: Mapped["Class"] = relationship(lazy="selectin")  # noqa: F821
    transactions: Mapped[list["FeeTransaction"]] = relationship(
        back_populates="fee_structure", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<FeeStructure id={self.id} head={self.fee_head!r} amount={self.amount}>"


class FeeTransaction(Base):
    """Record of a fee payment by a student."""

    __tablename__ = "fee_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    fee_structure_id: Mapped[int] = mapped_column(ForeignKey("fee_structures.id"), nullable=False, index=True)
    amount_paid: Mapped[float] = mapped_column(Float, nullable=False)
    payment_mode: Mapped[PaymentMode] = mapped_column(
        Enum(PaymentMode, name="payment_mode", create_constraint=True),
        nullable=False,
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100))
    receipt_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True,
        comment="Auto-generated receipt number",
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    refund_reason: Mapped[str | None] = mapped_column(Text)

    # relationships
    student: Mapped["Student"] = relationship(back_populates="fee_transactions")  # noqa: F821
    fee_structure: Mapped["FeeStructure"] = relationship(back_populates="transactions")

    def __repr__(self) -> str:
        return f"<FeeTransaction id={self.id} receipt={self.receipt_number!r}>"

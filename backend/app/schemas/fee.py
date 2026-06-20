"""Fee schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field


class FeeStructureCreate(BaseModel):
    """Payload for defining a fee head for a class/year."""

    class_id: int
    academic_year_id: int
    fee_head: str = Field(..., max_length=100)
    amount: float = Field(..., gt=0)
    due_date: date
    term: str | None = None


class FeeStructureResponse(BaseModel):
    """Fee structure details."""

    id: int
    class_id: int
    academic_year_id: int
    fee_head: str
    amount: float
    due_date: date
    term: str | None = None

    model_config = {"from_attributes": True}


class FeeTransactionCreate(BaseModel):
    """Payload for recording a fee payment."""

    student_id: int
    fee_structure_id: int
    amount_paid: float = Field(..., gt=0)
    payment_mode: str = Field(..., pattern="^(cash|cheque|online)$")
    razorpay_payment_id: str | None = None


class FeeReceiptResponse(BaseModel):
    """Receipt returned after a payment is recorded."""

    id: int
    student_id: int
    fee_structure_id: int
    amount_paid: float
    payment_mode: str
    receipt_number: str
    razorpay_payment_id: str | None = None
    paid_at: datetime

    model_config = {"from_attributes": True}


class DefaulterResponse(BaseModel):
    """Student with outstanding fee balance."""

    student_id: int
    admission_number: str
    student_name: str
    class_name: str
    fee_head: str
    amount_due: float
    amount_paid: float
    balance: float
    due_date: date

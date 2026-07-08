"""Fee management endpoints — structure CRUD, payments, defaulters, Razorpay webhook."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.fee import FeeStructure, FeeTransaction, PaymentMode
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.fee import (
    DefaulterResponse,
    FeeReceiptResponse,
    FeeStructureCreate,
    FeeStructureResponse,
    FeeTransactionCreate,
)
from app.services import razorpay as razorpay_service

router = APIRouter(prefix="/fees", tags=["Fees"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


async def _generate_receipt_number(db: AsyncSession) -> str:
    """Generate a sequential receipt number like RCT-00001."""
    result = await db.execute(select(func.count(FeeTransaction.id)))
    count = result.scalar() or 0
    return f"RCT-{count + 1:05d}"


# ── Fee Structure CRUD ──────────────────────────────────────────────────


@router.post("/structures", response_model=FeeStructureResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_structure(
    payload: FeeStructureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> FeeStructureResponse:
    """Define a new fee head for a class/academic-year."""
    structure = FeeStructure(**payload.model_dump())
    db.add(structure)
    await db.flush()
    await db.refresh(structure)
    return FeeStructureResponse.model_validate(structure)


@router.get("/structures", response_model=List[FeeStructureResponse])
async def list_fee_structures(
    class_id: int | None = Query(None),
    academic_year_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[FeeStructureResponse]:
    """List fee structures with optional filters."""
    query = select(FeeStructure)
    if class_id:
        query = query.where(FeeStructure.class_id == class_id)
    if academic_year_id:
        query = query.where(FeeStructure.academic_year_id == academic_year_id)
    query = query.order_by(FeeStructure.due_date)
    result = await db.execute(query)
    return [FeeStructureResponse.model_validate(s) for s in result.scalars().all()]


@router.put("/structures/{structure_id}", response_model=FeeStructureResponse)
async def update_fee_structure(
    structure_id: int,
    payload: FeeStructureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> FeeStructureResponse:
    """Update an existing fee structure."""
    result = await db.execute(
        select(FeeStructure).where(FeeStructure.id == structure_id),
    )
    structure = result.scalar_one_or_none()
    if not structure:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    for field, value in payload.model_dump().items():
        setattr(structure, field, value)
    await db.flush()
    await db.refresh(structure)
    return FeeStructureResponse.model_validate(structure)


@router.delete("/structures/{structure_id}", response_model=MessageResponse)
async def delete_fee_structure(
    structure_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Delete a fee structure (only if no payments recorded)."""
    result = await db.execute(
        select(FeeStructure).where(FeeStructure.id == structure_id),
    )
    structure = result.scalar_one_or_none()
    if not structure:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    txn_count = await db.execute(
        select(func.count(FeeTransaction.id)).where(
            FeeTransaction.fee_structure_id == structure_id,
        )
    )
    if (txn_count.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: payments already recorded against this structure",
        )

    await db.delete(structure)
    await db.flush()
    return MessageResponse(message="Fee structure deleted")


# ── Payments ─────────────────────────────────────────────────────────────


@router.post("/pay", response_model=FeeReceiptResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    payload: FeeTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> FeeReceiptResponse:
    """Record a fee payment and generate a receipt."""
    # Validate student
    student = await db.execute(
        select(Student).where(Student.id == payload.student_id),
    )
    if not student.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")

    # Validate fee structure
    structure = await db.execute(
        select(FeeStructure).where(FeeStructure.id == payload.fee_structure_id),
    )
    if not structure.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Fee structure not found")

    receipt_number = await _generate_receipt_number(db)

    txn = FeeTransaction(
        student_id=payload.student_id,
        fee_structure_id=payload.fee_structure_id,
        amount_paid=payload.amount_paid,
        payment_mode=PaymentMode(payload.payment_mode),
        razorpay_payment_id=payload.razorpay_payment_id,
        receipt_number=receipt_number,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return FeeReceiptResponse.model_validate(txn)


@router.get("/transactions", response_model=List[FeeReceiptResponse])
async def list_transactions(
    student_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[FeeReceiptResponse]:
    """Payment history, newest first."""
    query = select(FeeTransaction)
    if student_id:
        query = query.where(FeeTransaction.student_id == student_id)
    if date_from:
        query = query.where(FeeTransaction.paid_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(FeeTransaction.paid_at <= datetime.combine(date_to, datetime.max.time()))
    query = (
        query.order_by(FeeTransaction.paid_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return [FeeReceiptResponse.model_validate(t) for t in result.scalars().all()]


@router.get("/transactions/export.csv")
async def export_transactions_csv(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StreamingResponse:
    """Fee collection report as CSV (SRS 6.5)."""
    import csv
    import io

    query = select(FeeTransaction, Student).join(Student, Student.id == FeeTransaction.student_id)
    if date_from:
        query = query.where(FeeTransaction.paid_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.where(FeeTransaction.paid_at <= datetime.combine(date_to, datetime.max.time()))
    result = await db.execute(query.order_by(FeeTransaction.paid_at.desc()))

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["receipt_number", "date", "student", "admission_number", "amount", "mode", "payment_ref"])
    for txn, student in result.all():
        writer.writerow(
            [txn.receipt_number, txn.paid_at.isoformat() if txn.paid_at else "",
             f"{student.first_name} {student.last_name}", student.admission_number,
             txn.amount_paid, txn.payment_mode.value, txn.razorpay_payment_id or ""]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fee-transactions.csv"},
    )


@router.get("/defaulters/export.csv")
async def export_defaulters_csv(
    class_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StreamingResponse:
    """Defaulter list as CSV."""
    import csv
    import io

    defaulters = await get_defaulters(class_id=class_id, academic_year_id=None, as_of_date=None, db=db, current_user=current_user)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["student", "admission_number", "class", "fee_head", "due", "paid", "balance", "due_date"])
    for d in defaulters:
        writer.writerow(
            [d.student_name, d.admission_number, d.class_name, d.fee_head,
             d.amount_due, d.amount_paid, d.balance, d.due_date.isoformat()]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=defaulters.csv"},
    )


@router.get("/receipts/{txn_id}/html", response_class=HTMLResponse)
async def receipt_html(
    txn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES, UserRole.STUDENT, UserRole.PARENT)),
) -> HTMLResponse:
    """Printable fee receipt (FR-11). Students can open their own receipts."""
    txn = await db.get(FeeTransaction, txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Students/parents may only open receipts for their own linked student.
    if current_user.role in (UserRole.STUDENT, UserRole.PARENT):
        if current_user.linked_student_id != txn.student_id:
            raise HTTPException(status_code=403, detail="Not your receipt")

    student = await db.get(Student, txn.student_id)
    structure = await db.get(FeeStructure, txn.fee_structure_id)

    from app.models.academic import Class
    from app.models.school import School
    from app.services.certificates import generate_receipt

    class_ = await db.get(Class, student.class_id) if student else None
    school = (await db.execute(select(School))).scalars().first()

    html = await generate_receipt(
        {
            "receipt_number": txn.receipt_number,
            "paid_on": txn.paid_at.strftime("%d %b %Y") if txn.paid_at else "",
            "student_name": f"{student.first_name} {student.last_name}" if student else "",
            "admission_number": student.admission_number if student else "",
            "class_name": class_.name if class_ else "",
            "fee_head": structure.fee_head if structure else "",
            "term": structure.term if structure else None,
            "payment_mode": txn.payment_mode.value,
            "amount_paid": txn.amount_paid,
            "razorpay_payment_id": txn.razorpay_payment_id,
        },
        {
            "name": school.name if school else "",
            "address": school.address if school else "",
            "affiliation_number": school.affiliation_number if school else "",
        },
    )
    return HTMLResponse(content=html)


# ── Defaulters ──────────────────────────────────────────────────────────


@router.get("/defaulters", response_model=List[DefaulterResponse])
async def get_defaulters(
    class_id: int | None = Query(None),
    academic_year_id: int | None = Query(None),
    as_of_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[DefaulterResponse]:
    """List students with unpaid or partially paid fees."""
    cutoff = as_of_date or date.today()

    # All fee structures due by cutoff
    fs_filters = [FeeStructure.due_date <= cutoff]
    if class_id:
        fs_filters.append(FeeStructure.class_id == class_id)
    if academic_year_id:
        fs_filters.append(FeeStructure.academic_year_id == academic_year_id)

    from app.models.academic import Class

    paid_subq = (
        select(
            FeeTransaction.student_id,
            FeeTransaction.fee_structure_id,
            func.coalesce(func.sum(FeeTransaction.amount_paid), 0).label("total_paid"),
        )
        .group_by(FeeTransaction.student_id, FeeTransaction.fee_structure_id)
        .subquery()
    )

    query = (
        select(
            Student.id.label("student_id"),
            Student.admission_number,
            (Student.first_name + " " + Student.last_name).label("student_name"),
            Class.name.label("class_name"),
            FeeStructure.fee_head,
            FeeStructure.amount.label("amount_due"),
            func.coalesce(paid_subq.c.total_paid, 0).label("amount_paid"),
            (FeeStructure.amount - func.coalesce(paid_subq.c.total_paid, 0)).label("balance"),
            FeeStructure.due_date,
        )
        .join(FeeStructure, FeeStructure.class_id == Student.class_id)
        .join(Class, Class.id == Student.class_id)
        .outerjoin(
            paid_subq,
            and_(
                paid_subq.c.student_id == Student.id,
                paid_subq.c.fee_structure_id == FeeStructure.id,
            ),
        )
        .where(
            and_(
                Student.is_active == True,  # noqa: E712
                *fs_filters,
                (FeeStructure.amount - func.coalesce(paid_subq.c.total_paid, 0)) > 0,
            )
        )
        .order_by(Student.id, FeeStructure.due_date)
    )

    result = await db.execute(query)
    return [
        DefaulterResponse(
            student_id=row.student_id,
            admission_number=row.admission_number,
            student_name=row.student_name,
            class_name=row.class_name,
            fee_head=row.fee_head,
            amount_due=float(row.amount_due),
            amount_paid=float(row.amount_paid),
            balance=float(row.balance),
            due_date=row.due_date,
        )
        for row in result.all()
    ]


# ── Student self-service (SRS 8.7) ──────────────────────────────────────


@router.get("/my")
async def my_fee_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> dict:
    """Fee dues, payment history, and balances for the signed-in student."""
    if current_user.linked_student_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a student record")
    student = await db.get(Student, current_user.linked_student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student record not found")

    structures = (
        await db.execute(
            select(FeeStructure)
            .where(FeeStructure.class_id == student.class_id)
            .order_by(FeeStructure.due_date)
        )
    ).scalars().all()
    transactions = (
        await db.execute(
            select(FeeTransaction)
            .where(FeeTransaction.student_id == student.id)
            .order_by(FeeTransaction.paid_at.desc())
        )
    ).scalars().all()

    paid_by_structure: dict[int, float] = {}
    for txn in transactions:
        paid_by_structure[txn.fee_structure_id] = (
            paid_by_structure.get(txn.fee_structure_id, 0.0) + txn.amount_paid
        )

    return {
        "student_id": student.id,
        "items": [
            {
                "fee_structure_id": s.id,
                "fee_head": s.fee_head,
                "term": s.term,
                "amount": s.amount,
                "due_date": s.due_date.isoformat(),
                "paid": paid_by_structure.get(s.id, 0.0),
                "balance": max(0.0, s.amount - paid_by_structure.get(s.id, 0.0)),
            }
            for s in structures
        ],
        "transactions": [
            {
                "id": t.id,
                "receipt_number": t.receipt_number,
                "amount_paid": t.amount_paid,
                "payment_mode": t.payment_mode.value,
                "paid_at": t.paid_at.isoformat() if t.paid_at else None,
            }
            for t in transactions
        ],
    }


# ── Razorpay online payment (SRS 8.7 "Pay Now", FR-12) ──────────────────


class RazorpayOrderRequest(BaseModel):
    fee_structure_id: int


class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    fee_structure_id: int
    amount: float = Field(..., gt=0)


@router.post("/razorpay/order")
async def create_razorpay_order(
    payload: RazorpayOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> dict:
    """Create a Razorpay order for the outstanding balance of a fee head."""
    if not razorpay_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online payments are not configured yet — pay at the school office",
        )
    if current_user.linked_student_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a student record")

    structure = await db.get(FeeStructure, payload.fee_structure_id)
    if structure is None:
        raise HTTPException(status_code=404, detail="Fee structure not found")

    paid = (
        await db.execute(
            select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0)).where(
                FeeTransaction.student_id == current_user.linked_student_id,
                FeeTransaction.fee_structure_id == structure.id,
            )
        )
    ).scalar() or 0
    balance = structure.amount - float(paid)
    if balance <= 0:
        raise HTTPException(status_code=409, detail="This fee is already fully paid")

    order = await razorpay_service.create_order(
        amount_paise=int(round(balance * 100)),
        receipt=f"stu{current_user.linked_student_id}-fs{structure.id}",
        notes={
            "student_id": str(current_user.linked_student_id),
            "fee_structure_id": str(structure.id),
        },
    )
    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": settings.razorpay_key_id,
        "fee_head": structure.fee_head,
    }


@router.post("/razorpay/verify", response_model=FeeReceiptResponse, status_code=status.HTTP_201_CREATED)
async def verify_razorpay_payment(
    payload: RazorpayVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> FeeReceiptResponse:
    """Verify a completed Razorpay checkout and record the transaction (FR-12)."""
    if current_user.linked_student_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a student record")

    valid = await razorpay_service.verify_payment_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    # Idempotency: never record the same payment twice.
    existing = (
        await db.execute(
            select(FeeTransaction).where(
                FeeTransaction.razorpay_payment_id == payload.razorpay_payment_id
            )
        )
    ).scalar_one_or_none()
    if existing:
        return FeeReceiptResponse.model_validate(existing)

    receipt_number = await _generate_receipt_number(db)
    txn = FeeTransaction(
        student_id=current_user.linked_student_id,
        fee_structure_id=payload.fee_structure_id,
        amount_paid=payload.amount,
        payment_mode=PaymentMode.ONLINE,
        razorpay_payment_id=payload.razorpay_payment_id,
        receipt_number=receipt_number,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return FeeReceiptResponse.model_validate(txn)


@router.post("/reminders/dispatch", response_model=MessageResponse)
async def dispatch_fee_reminders(
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Send WhatsApp due reminders to every defaulter's parents (SRS 6.5)."""
    from app.services.automations import send_fee_reminders

    sent = await send_fee_reminders()
    if sent == -1:
        raise HTTPException(
            status_code=409,
            detail="Fee reminders are switched off — enable them in Settings → Automation",
        )
    return MessageResponse(
        message=f"Reminders queued to {sent} parents (see Communication Log for delivery status)"
    )


# ── Razorpay Webhook ────────────────────────────────────────────────────


@router.post("/razorpay/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Handle Razorpay payment webhooks.

    Verifies the signature, extracts payment info, and updates the
    corresponding transaction record.
    """
    signature = request.headers.get("X-Razorpay-Signature", "")
    raw_body = await request.body()

    event = await razorpay_service.process_webhook(raw_body, signature)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("event", "")
    if event_type == "payment.captured":
        payment = event.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_payment_id = payment.get("id")
        if razorpay_payment_id:
            result = await db.execute(
                select(FeeTransaction).where(
                    FeeTransaction.razorpay_payment_id == razorpay_payment_id,
                )
            )
            txn = result.scalar_one_or_none()
            if txn:
                txn.paid_at = datetime.utcnow()
                await db.flush()

    return {"status": "ok"}

"""Reporting service — attendance trends, fee summaries, admission funnel."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admission import AdmissionEnquiry, EnquiryStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.fee import FeeStructure, FeeTransaction


async def attendance_trends(
    db: AsyncSession,
    class_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> List[Dict[str, Any]]:
    """Return daily attendance counts grouped by date.

    Each row contains ``date``, ``present``, ``absent``, ``late``, ``total``.
    """
    filters = []
    if start_date:
        filters.append(Attendance.date >= start_date)
    if end_date:
        filters.append(Attendance.date <= end_date)

    # Join students table if class filter is needed
    from app.models.student import Student

    if class_id:
        filters.append(Student.class_id == class_id)

    query = (
        select(
            Attendance.date.label("date"),
            func.count().label("total"),
            func.count(case((Attendance.status == AttendanceStatus.PRESENT, 1))).label("present"),
            func.count(case((Attendance.status == AttendanceStatus.ABSENT, 1))).label("absent"),
            func.count(case((Attendance.status == AttendanceStatus.LATE, 1))).label("late"),
        )
        .join(Student, Student.id == Attendance.student_id)
        .where(and_(*filters) if filters else True)
        .group_by(Attendance.date)
        .order_by(Attendance.date)
    )

    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "date": str(row.date),
            "total": row.total,
            "present": row.present,
            "absent": row.absent,
            "late": row.late,
        }
        for row in rows
    ]


async def fee_collection_summary(
    db: AsyncSession,
    academic_year_id: int | None = None,
) -> Dict[str, Any]:
    """Return aggregate fee collection vs pending totals.

    Returns:
        Dict with ``total_expected``, ``total_collected``, ``total_pending``,
        and a list of per-fee-head breakdowns.
    """
    fs_filters = []
    if academic_year_id:
        fs_filters.append(FeeStructure.academic_year_id == academic_year_id)

    # Total expected
    expected_q = select(func.coalesce(func.sum(FeeStructure.amount), 0)).where(
        and_(*fs_filters) if fs_filters else True,
    )
    expected_result = await db.execute(expected_q)
    total_expected = float(expected_result.scalar() or 0)

    # Total collected
    collected_q = select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0))
    if academic_year_id:
        collected_q = collected_q.join(
            FeeStructure, FeeStructure.id == FeeTransaction.fee_structure_id,
        ).where(FeeStructure.academic_year_id == academic_year_id)
    collected_result = await db.execute(collected_q)
    total_collected = float(collected_result.scalar() or 0)

    # Per fee-head breakdown
    breakdown_q = (
        select(
            FeeStructure.fee_head,
            func.coalesce(func.sum(FeeStructure.amount), 0).label("expected"),
            func.coalesce(func.sum(FeeTransaction.amount_paid), 0).label("collected"),
        )
        .outerjoin(FeeTransaction, FeeTransaction.fee_structure_id == FeeStructure.id)
        .where(and_(*fs_filters) if fs_filters else True)
        .group_by(FeeStructure.fee_head)
    )
    breakdown_result = await db.execute(breakdown_q)
    heads = [
        {
            "fee_head": row.fee_head,
            "expected": float(row.expected),
            "collected": float(row.collected),
            "pending": float(row.expected) - float(row.collected),
        }
        for row in breakdown_result.all()
    ]

    return {
        "total_expected": total_expected,
        "total_collected": total_collected,
        "total_pending": total_expected - total_collected,
        "by_fee_head": heads,
    }


async def admission_funnel(db: AsyncSession) -> Dict[str, Any]:
    """Return admission enquiry counts grouped by pipeline status.

    Returns:
        Dict with status→count mapping and a ``total`` key.
    """
    query = select(
        AdmissionEnquiry.status,
        func.count().label("count"),
    ).group_by(AdmissionEnquiry.status)

    result = await db.execute(query)
    rows = result.all()

    funnel: Dict[str, int] = {s.value: 0 for s in EnquiryStatus}
    total = 0
    for row in rows:
        funnel[row.status.value] = row.count
        total += row.count

    conversion = 0.0
    if total > 0 and funnel.get("admitted", 0) > 0:
        conversion = round(funnel["admitted"] / total * 100, 2)

    return {
        "funnel": funnel,
        "total": total,
        "conversion_rate_percent": conversion,
    }

"""Reporting service — attendance trends, fee summaries, admission funnel."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Class
from app.models.admission import AdmissionEnquiry, EnquiryStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.fee import FeeStructure, FeeTransaction
from app.models.notice import Notice
from app.models.staff import Staff
from app.models.student import Student
from app.schemas.dashboard import (
    ActivityItem,
    AdminDashboardResponse,
    ClassAttendanceBar,
    KpiValue,
    MonthlyPoint,
)


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


def _month_bounds(months_ago: int, from_date: date) -> tuple[datetime, datetime]:
    """[start, end) datetime bounds for the calendar month `months_ago` before from_date."""
    year = from_date.year
    month = from_date.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _pct_change(current: float, previous: float) -> float | None:
    """Percent change, or None when a baseline doesn't exist (never fake a trend)."""
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


async def admin_dashboard_summary(db: AsyncSession) -> AdminDashboardResponse:
    """Aggregate everything the admin dashboard needs, in one call.

    Every trend is computed from a real prior baseline — when that baseline
    doesn't exist (e.g. no staff.created_at to compare against), the trend
    is omitted rather than shown as 0% or invented.
    """
    today = date.today()
    # Timezone-AWARE (not utcnow()) so the serialized ISO string carries a
    # 'Z'/offset — a naive string gets misparsed as local time by browsers,
    # which silently skews every "Xh ago" label by the viewer's UTC offset.
    now = datetime.now(timezone.utc)

    # ── Students: total + 30-day growth trend (Student.created_at exists) ──
    total_students = (
        await db.execute(select(func.count(Student.id)).where(Student.is_active))
    ).scalar() or 0
    thirty_days_ago = now - timedelta(days=30)
    students_30d_ago = (
        await db.execute(
            select(func.count(Student.id)).where(
                Student.is_active, Student.created_at <= thirty_days_ago
            )
        )
    ).scalar() or 0
    students_kpi = KpiValue(
        value=total_students,
        trend_percent=_pct_change(total_students, students_30d_ago) if students_30d_ago else None,
    )

    # ── Staff: total only — no created_at on Staff, so no trend to compute ──
    total_staff = (
        await db.execute(select(func.count(Staff.id)).where(Staff.is_active))
    ).scalar() or 0
    staff_kpi = KpiValue(value=total_staff, trend_percent=None)

    # ── Fees: this month collected vs last month, real % change ────────────
    this_month_start, next_month_start = _month_bounds(0, today)
    last_month_start, last_month_end = _month_bounds(1, today)
    this_month_collected = (
        await db.execute(
            select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0)).where(
                FeeTransaction.paid_at >= this_month_start,
                FeeTransaction.paid_at < next_month_start,
            )
        )
    ).scalar() or 0
    last_month_collected = (
        await db.execute(
            select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0)).where(
                FeeTransaction.paid_at >= last_month_start,
                FeeTransaction.paid_at < last_month_end,
            )
        )
    ).scalar() or 0
    fees_kpi = KpiValue(
        value=float(this_month_collected),
        trend_percent=_pct_change(float(this_month_collected), float(last_month_collected)),
    )

    # Real per-student pending balance — NOT sum(FeeStructure.amount), which
    # is a per-class rate and would wildly undercount actual dues owed.
    # Mirrors the same per-student-per-structure math /fees/defaulters uses.
    structures = (await db.execute(select(FeeStructure))).scalars().all()
    students_by_class: dict[int, list[int]] = {}
    for row in await db.execute(select(Student.id, Student.class_id).where(Student.is_active)):
        students_by_class.setdefault(row.class_id, []).append(row.id)
    paid_by_pair: dict[tuple[int, int], float] = {}
    paid_rows = await db.execute(
        select(
            FeeTransaction.student_id,
            FeeTransaction.fee_structure_id,
            func.sum(FeeTransaction.amount_paid),
        ).group_by(FeeTransaction.student_id, FeeTransaction.fee_structure_id)
    )
    for student_id, structure_id, total_paid in paid_rows.all():
        paid_by_pair[(student_id, structure_id)] = float(total_paid or 0)

    fees_pending = 0.0
    for structure in structures:
        for student_id in students_by_class.get(structure.class_id, []):
            paid = paid_by_pair.get((student_id, structure.id), 0.0)
            fees_pending += max(0.0, structure.amount - paid)

    new_enquiries = (
        await db.execute(
            select(func.count(AdmissionEnquiry.id)).where(
                AdmissionEnquiry.status == EnquiryStatus.NEW
            )
        )
    ).scalar() or 0

    # ── Fee collection — last 6 calendar months, zero-filled ───────────────
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fee_collection_by_month: list[MonthlyPoint] = []
    for months_ago in range(5, -1, -1):
        start, end = _month_bounds(months_ago, today)
        amount = (
            await db.execute(
                select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0)).where(
                    FeeTransaction.paid_at >= start, FeeTransaction.paid_at < end
                )
            )
        ).scalar() or 0
        fee_collection_by_month.append(
            MonthlyPoint(
                month=f"{start.year:04d}-{start.month:02d}",
                label=month_labels[start.month - 1],
                amount=float(amount),
            )
        )

    # ── Attendance by class — this week (Mon..today), classes with data only
    week_start = today - timedelta(days=today.weekday())
    attendance_rows = await db.execute(
        select(
            Class.name,
            func.count().label("total"),
            func.count(
                case((Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]), 1))
            ).label("present"),
        )
        .select_from(Attendance)
        .join(Student, Student.id == Attendance.student_id)
        .join(Class, Class.id == Student.class_id)
        .where(Attendance.date >= week_start, Attendance.date <= today)
        .group_by(Class.name, Class.numeric_order)
        .order_by(Class.numeric_order)
    )
    attendance_by_class = [
        ClassAttendanceBar(
            class_name=row.name,
            percentage=round(row.present / row.total * 100, 1) if row.total else 0.0,
        )
        for row in attendance_rows.all()
    ]

    # ── Recent activity feed — notices, enquiries, payments merged ─────────
    activity: list[ActivityItem] = []

    recent_notices = (
        await db.execute(
            select(Notice)
            .where(Notice.published_at.is_not(None))
            .order_by(Notice.published_at.desc())
            .limit(5)
        )
    ).scalars().all()
    activity += [
        ActivityItem(type="notice", text=f"Notice published: {n.title}", at=n.published_at)
        for n in recent_notices
    ]

    recent_enquiries = (
        await db.execute(
            select(AdmissionEnquiry).order_by(AdmissionEnquiry.created_at.desc()).limit(5)
        )
    ).scalars().all()
    activity += [
        ActivityItem(
            type="enquiry",
            text=f"New admission enquiry: {e.child_name} ({e.class_applying})",
            at=e.created_at,
        )
        for e in recent_enquiries
    ]

    recent_payments = (
        await db.execute(
            select(FeeTransaction, Student)
            .join(Student, Student.id == FeeTransaction.student_id)
            .order_by(FeeTransaction.paid_at.desc())
            .limit(5)
        )
    ).all()
    activity += [
        ActivityItem(
            type="payment",
            text=f"₹{txn.amount_paid:,.0f} received from {student.first_name} {student.last_name}",
            at=txn.paid_at,
        )
        for txn, student in recent_payments
    ]

    activity.sort(key=lambda item: item.at, reverse=True)

    return AdminDashboardResponse(
        total_students=students_kpi,
        total_staff=staff_kpi,
        fees_collected=fees_kpi,
        fees_pending=round(fees_pending, 2),
        new_enquiries=new_enquiries,
        fee_collection_by_month=fee_collection_by_month,
        attendance_by_class=attendance_by_class,
        recent_activity=activity[:8],
        generated_at=now,
    )

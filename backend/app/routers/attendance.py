"""Attendance endpoints — mark, history, override."""

from __future__ import annotations

from datetime import date
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.attendance import Attendance, AttendanceStatus, StaffAttendance
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceMarkRequest,
    AttendanceOverrideRequest,
    AttendanceResponse,
    StaffAttendanceMarkRequest,
    StaffAttendanceResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/attendance", tags=["Attendance"])

MARKER_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER)


@router.post("/mark", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    payload: AttendanceMarkRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*MARKER_ROLES)),
) -> MessageResponse:
    """Bulk-mark attendance for a class/section on a given date.

    If a record already exists for a student+date+period, it is updated
    rather than duplicated. Absences trigger a WhatsApp alert to parents
    when the automation is enabled (FR-9).
    """
    created = 0
    updated = 0

    for entry in payload.entries:
        existing_result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.student_id == entry.student_id,
                    Attendance.date == payload.date,
                    Attendance.period == payload.period,
                )
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.status = AttendanceStatus(entry.status)
            existing.marked_by_id = current_user.id
            updated += 1
        else:
            db.add(Attendance(
                student_id=entry.student_id,
                date=payload.date,
                status=AttendanceStatus(entry.status),
                marked_by_id=current_user.id,
                period=payload.period,
            ))
            created += 1

    await db.flush()

    absent_ids = [e.student_id for e in payload.entries if e.status == "absent"]
    if absent_ids:
        from app.services.automations import send_absent_alerts

        background_tasks.add_task(send_absent_alerts, absent_ids, payload.date)

    return MessageResponse(message=f"Attendance marked: {created} created, {updated} updated")


@router.get("/", response_model=List[AttendanceResponse])
async def get_attendance_history(
    class_id: int | None = Query(None),
    section_id: int | None = Query(None),
    student_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    attendance_date: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*MARKER_ROLES)),
) -> List[AttendanceResponse]:
    """Retrieve attendance records with filters."""
    from app.models.student import Student

    query = select(Attendance).join(Student, Student.id == Attendance.student_id)
    filters = []

    if student_id:
        filters.append(Attendance.student_id == student_id)
    if class_id:
        filters.append(Student.class_id == class_id)
    if section_id:
        filters.append(Student.section_id == section_id)
    if attendance_date:
        filters.append(Attendance.date == attendance_date)
    if date_from:
        filters.append(Attendance.date >= date_from)
    if date_to:
        filters.append(Attendance.date <= date_to)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Attendance.date.desc(), Attendance.student_id)
    result = await db.execute(query)
    return [AttendanceResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/export.csv")
async def export_attendance_csv(
    class_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)),
):
    """Attendance records as CSV (SRS 6.6 reports)."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    from app.models.student import Student

    query = (
        select(Attendance, Student)
        .join(Student, Student.id == Attendance.student_id)
        .order_by(Attendance.date.desc(), Student.roll_number)
    )
    if class_id:
        query = query.where(Student.class_id == class_id)
    if date_from:
        query = query.where(Attendance.date >= date_from)
    if date_to:
        query = query.where(Attendance.date <= date_to)
    result = await db.execute(query)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "student", "admission_number", "class_id", "status", "period", "override_reason"])
    for record, student in result.all():
        writer.writerow(
            [record.date.isoformat(), f"{student.first_name} {student.last_name}",
             student.admission_number, student.class_id, record.status.value,
             record.period or "", record.override_reason or ""]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"},
    )


@router.get("/my", response_model=dict)
async def my_attendance(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> dict:
    """The signed-in student's own attendance history + percentage (SRS 8.2)."""
    if current_user.linked_student_id is None:
        return {"records": [], "present": 0, "absent": 0, "late": 0, "percentage": None}

    query = select(Attendance).where(Attendance.student_id == current_user.linked_student_id)
    if date_from:
        query = query.where(Attendance.date >= date_from)
    if date_to:
        query = query.where(Attendance.date <= date_to)
    query = query.order_by(Attendance.date.desc())
    result = await db.execute(query)
    records = result.scalars().all()

    present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
    late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
    absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    total = len(records)
    return {
        "records": [
            {"date": r.date.isoformat(), "status": r.status.value, "period": r.period}
            for r in records
        ],
        "present": present,
        "absent": absent,
        "late": late,
        "percentage": round((present + late) / total * 100, 1) if total else None,
    }


# ── Staff attendance (SRS 6.3 / 6.6) ────────────────────────────────────


@router.post("/staff/mark", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def mark_staff_attendance(
    payload: StaffAttendanceMarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)),
) -> MessageResponse:
    """Bulk-mark staff attendance for a date (upserts per staff+date)."""
    created = 0
    updated = 0
    for entry in payload.entries:
        existing_result = await db.execute(
            select(StaffAttendance).where(
                and_(
                    StaffAttendance.staff_id == entry.staff_id,
                    StaffAttendance.date == payload.date,
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            existing.status = AttendanceStatus(entry.status)
            updated += 1
        else:
            db.add(
                StaffAttendance(
                    staff_id=entry.staff_id,
                    date=payload.date,
                    status=AttendanceStatus(entry.status),
                )
            )
            created += 1

    await db.flush()
    return MessageResponse(message=f"Staff attendance marked: {created} created, {updated} updated")


@router.get("/staff", response_model=List[StaffAttendanceResponse])
async def get_staff_attendance(
    staff_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    attendance_date: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)),
) -> List[StaffAttendanceResponse]:
    """Staff attendance records with filters."""
    query = select(StaffAttendance)
    filters = []
    if staff_id:
        filters.append(StaffAttendance.staff_id == staff_id)
    if attendance_date:
        filters.append(StaffAttendance.date == attendance_date)
    if date_from:
        filters.append(StaffAttendance.date >= date_from)
    if date_to:
        filters.append(StaffAttendance.date <= date_to)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(StaffAttendance.date.desc(), StaffAttendance.staff_id)
    result = await db.execute(query)
    return [StaffAttendanceResponse.model_validate(r) for r in result.scalars().all()]


@router.put("/{attendance_id}/override", response_model=AttendanceResponse)
async def override_attendance(
    attendance_id: int,
    payload: AttendanceOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)),
) -> AttendanceResponse:
    """Override an existing attendance record with a mandatory reason."""
    result = await db.execute(
        select(Attendance).where(Attendance.id == attendance_id),
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    record.status = AttendanceStatus(payload.status)
    record.override_reason = payload.reason
    record.marked_by_id = current_user.id
    await db.flush()
    await db.refresh(record)
    return AttendanceResponse.model_validate(record)

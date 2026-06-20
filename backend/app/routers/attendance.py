"""Attendance endpoints — mark, history, override."""

from __future__ import annotations

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.attendance import Attendance, AttendanceStatus
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceMarkRequest,
    AttendanceOverrideRequest,
    AttendanceResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/attendance", tags=["Attendance"])

MARKER_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER)


@router.post("/mark", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    payload: AttendanceMarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*MARKER_ROLES)),
) -> MessageResponse:
    """Bulk-mark attendance for a class/section on a given date.

    If a record already exists for a student+date+period, it is updated
    rather than duplicated.
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

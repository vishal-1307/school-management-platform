"""Timetable endpoints — CRUD with conflict detection."""

from __future__ import annotations

from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.timetable import TimetableSlot
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.timetable import (
    DaySchedule,
    TimetableSlotCreate,
    TimetableSlotResponse,
    WeeklyTimetableResponse,
)

router = APIRouter(prefix="/timetable", tags=["Timetable"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


@router.post("/slots", response_model=TimetableSlotResponse, status_code=status.HTTP_201_CREATED)
async def create_slot(
    payload: TimetableSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> TimetableSlotResponse:
    """Add a new timetable slot with conflict detection.

    Checks for:
    1. Duplicate slot for the same class-section-day-period.
    2. Staff already assigned to another class at the same day-period.
    """
    # Check class-section-day-period conflict
    existing = await db.execute(
        select(TimetableSlot).where(
            and_(
                TimetableSlot.class_id == payload.class_id,
                TimetableSlot.section_id == payload.section_id,
                TimetableSlot.day_of_week == payload.day_of_week,
                TimetableSlot.period_number == payload.period_number,
                TimetableSlot.is_substitute == False,  # noqa: E712
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Slot already exists for {payload.day_of_week} period {payload.period_number}",
        )

    # Check staff conflict
    staff_conflict = await db.execute(
        select(TimetableSlot).where(
            and_(
                TimetableSlot.staff_id == payload.staff_id,
                TimetableSlot.day_of_week == payload.day_of_week,
                TimetableSlot.period_number == payload.period_number,
                TimetableSlot.is_substitute == False,  # noqa: E712
            )
        )
    )
    if staff_conflict.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Staff member already assigned on {payload.day_of_week} period {payload.period_number}",
        )

    slot = TimetableSlot(**payload.model_dump())
    db.add(slot)
    await db.flush()
    await db.refresh(slot)
    return TimetableSlotResponse.model_validate(slot)


@router.get("/weekly", response_model=WeeklyTimetableResponse)
async def get_weekly_timetable(
    class_id: int = Query(...),
    section_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER,
        UserRole.STUDENT, UserRole.PARENT,
    )),
) -> WeeklyTimetableResponse:
    """Retrieve the full weekly timetable for a class-section."""
    result = await db.execute(
        select(TimetableSlot).where(
            and_(
                TimetableSlot.class_id == class_id,
                TimetableSlot.section_id == section_id,
            )
        ).order_by(TimetableSlot.period_number)
    )
    slots = result.scalars().all()

    days_map: dict[str, list[TimetableSlotResponse]] = defaultdict(list)
    for slot in slots:
        days_map[slot.day_of_week].append(TimetableSlotResponse.model_validate(slot))

    day_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    schedule = [
        DaySchedule(day=day, slots=days_map.get(day, []))
        for day in day_order
        if day in days_map
    ]

    return WeeklyTimetableResponse(
        class_id=class_id,
        section_id=section_id,
        schedule=schedule,
    )


@router.get("/my", response_model=List[TimetableSlotResponse])
async def my_timetable(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
) -> List[TimetableSlotResponse]:
    """The signed-in teacher's personal weekly schedule (SRS 7.2)."""
    if current_user.linked_staff_id is None:
        return []
    result = await db.execute(
        select(TimetableSlot)
        .where(TimetableSlot.staff_id == current_user.linked_staff_id)
        .order_by(TimetableSlot.period_number)
    )
    return [TimetableSlotResponse.model_validate(s) for s in result.scalars().all()]


@router.put("/slots/{slot_id}", response_model=TimetableSlotResponse)
async def update_slot(
    slot_id: int,
    payload: TimetableSlotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> TimetableSlotResponse:
    """Update an existing timetable slot."""
    result = await db.execute(
        select(TimetableSlot).where(TimetableSlot.id == slot_id),
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    for field, value in payload.model_dump().items():
        setattr(slot, field, value)

    await db.flush()
    await db.refresh(slot)
    return TimetableSlotResponse.model_validate(slot)


@router.delete("/slots/{slot_id}", response_model=MessageResponse)
async def delete_slot(
    slot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Delete a timetable slot."""
    result = await db.execute(
        select(TimetableSlot).where(TimetableSlot.id == slot_id),
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    await db.delete(slot)
    await db.flush()
    return MessageResponse(message="Timetable slot deleted")

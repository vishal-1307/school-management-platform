"""Staff CRUD endpoints with assignment management."""

from __future__ import annotations

import math
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import require_role
from app.models.staff import Staff, StaffSubjectAssignment
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.staff import StaffCreate, StaffResponse, StaffSubjectAssignmentSchema, StaffUpdate

router = APIRouter(prefix="/staff", tags=["Staff"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StaffResponse:
    """Create a new staff member with optional subject assignments."""
    staff = Staff(
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        photo_url=payload.photo_url,
        qualification=payload.qualification,
        designation=payload.designation,
    )
    db.add(staff)
    await db.flush()

    for a in payload.assignments:
        db.add(StaffSubjectAssignment(
            staff_id=staff.id,
            subject_id=a.subject_id,
            class_id=a.class_id,
            section_id=a.section_id,
        ))

    await db.flush()
    await db.refresh(staff, attribute_names=["subject_assignments"])
    return StaffResponse.model_validate(staff)


@router.get("/", response_model=List[StaffResponse])
async def list_staff(
    is_active: bool = Query(True),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[StaffResponse]:
    """List all staff members with optional search."""
    query = select(Staff).options(selectinload(Staff.subject_assignments))
    query = query.where(Staff.is_active == is_active)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Staff.first_name.ilike(pattern))
            | (Staff.last_name.ilike(pattern))
            | (Staff.phone.ilike(pattern))
        )
    query = query.order_by(Staff.id)
    result = await db.execute(query)
    return [StaffResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/me", response_model=StaffResponse)
async def get_my_staff_record(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
) -> StaffResponse:
    """The signed-in teacher's own record incl. teaching assignments (SRS 7.2)."""
    if current_user.linked_staff_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a staff record")
    result = await db.execute(
        select(Staff)
        .options(selectinload(Staff.subject_assignments))
        .where(Staff.id == current_user.linked_staff_id),
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff record not found")
    return StaffResponse.model_validate(staff)


@router.put("/me", response_model=StaffResponse)
async def update_my_staff_record(
    payload: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
) -> StaffResponse:
    """Teacher self-service profile update — contact details and photo only (SRS 7.9)."""
    if current_user.linked_staff_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a staff record")
    staff = await db.get(Staff, current_user.linked_staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff record not found")

    allowed = {"phone", "email", "photo_url", "qualification"}
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in allowed:
            setattr(staff, field, value)
    await db.flush()
    result = await db.execute(
        select(Staff)
        .options(selectinload(Staff.subject_assignments))
        .where(Staff.id == staff.id),
    )
    return StaffResponse.model_validate(result.scalar_one())


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StaffResponse:
    """Get a single staff member by ID."""
    result = await db.execute(
        select(Staff).options(selectinload(Staff.subject_assignments)).where(Staff.id == staff_id),
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return StaffResponse.model_validate(staff)


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StaffResponse:
    """Update a staff member's details (partial update)."""
    result = await db.execute(
        select(Staff).options(selectinload(Staff.subject_assignments)).where(Staff.id == staff_id),
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)

    await db.flush()
    await db.refresh(staff)
    return StaffResponse.model_validate(staff)


@router.delete("/{staff_id}", response_model=MessageResponse)
async def delete_staff(
    staff_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Soft-delete a staff member by setting is_active=False."""
    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    staff.is_active = False
    await db.flush()
    return MessageResponse(message=f"Staff {staff.first_name} {staff.last_name} deactivated")


@router.post("/{staff_id}/assignments", response_model=StaffResponse)
async def add_assignment(
    staff_id: int,
    payload: StaffSubjectAssignmentSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StaffResponse:
    """Add a subject-class-section assignment to a staff member."""
    result = await db.execute(
        select(Staff).options(selectinload(Staff.subject_assignments)).where(Staff.id == staff_id),
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Check for duplicate
    existing = await db.execute(
        select(StaffSubjectAssignment).where(
            StaffSubjectAssignment.staff_id == staff_id,
            StaffSubjectAssignment.subject_id == payload.subject_id,
            StaffSubjectAssignment.class_id == payload.class_id,
            StaffSubjectAssignment.section_id == payload.section_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Assignment already exists")

    db.add(StaffSubjectAssignment(
        staff_id=staff_id,
        subject_id=payload.subject_id,
        class_id=payload.class_id,
        section_id=payload.section_id,
    ))
    await db.flush()
    await db.refresh(staff, attribute_names=["subject_assignments"])
    return StaffResponse.model_validate(staff)


@router.delete("/{staff_id}/assignments/{assignment_id}", response_model=MessageResponse)
async def remove_assignment(
    staff_id: int,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Remove a subject assignment from a staff member."""
    result = await db.execute(
        select(StaffSubjectAssignment).where(
            StaffSubjectAssignment.id == assignment_id,
            StaffSubjectAssignment.staff_id == staff_id,
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    await db.delete(assignment)
    await db.flush()
    return MessageResponse(message="Assignment removed")

"""Teacher-assignment scoping helpers.

Role checks alone (require_role) only prove *what kind* of user is
calling — they don't prove the teacher is actually assigned to the
class/section/subject they're trying to act on. These helpers close that
gap for attendance, marks, the student roster, and homework review.
Admins always pass (they have school-wide access by design).
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import StaffSubjectAssignment
from app.models.user import User, UserRole

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)

_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You are not assigned to this class/section/subject",
)


async def require_class_section_scope(
    db: AsyncSession, user: User, class_id: int, section_id: int
) -> None:
    """A teacher may act here only if assigned to ANY subject in this class/section."""
    if user.role in ADMIN_ROLES:
        return
    if user.role != UserRole.TEACHER or not user.linked_staff_id:
        raise _FORBIDDEN
    result = await db.execute(
        select(StaffSubjectAssignment.id).where(
            StaffSubjectAssignment.staff_id == user.linked_staff_id,
            StaffSubjectAssignment.class_id == class_id,
            StaffSubjectAssignment.section_id == section_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise _FORBIDDEN


async def require_subject_class_scope(
    db: AsyncSession, user: User, subject_id: int, class_id: int
) -> None:
    """A teacher may act here only if assigned to this exact subject in this class."""
    if user.role in ADMIN_ROLES:
        return
    if user.role != UserRole.TEACHER or not user.linked_staff_id:
        raise _FORBIDDEN
    result = await db.execute(
        select(StaffSubjectAssignment.id).where(
            StaffSubjectAssignment.staff_id == user.linked_staff_id,
            StaffSubjectAssignment.subject_id == subject_id,
            StaffSubjectAssignment.class_id == class_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise _FORBIDDEN


async def teacher_assigned_class_ids(db: AsyncSession, staff_id: int) -> set[int]:
    """Every class_id this teacher has at least one subject assignment in."""
    result = await db.execute(
        select(StaffSubjectAssignment.class_id).where(
            StaffSubjectAssignment.staff_id == staff_id
        )
    )
    return {row[0] for row in result.all()}

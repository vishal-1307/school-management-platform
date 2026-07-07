"""Staff leave applications — teacher self-service + admin approvals (SRS §7.8)."""

from __future__ import annotations

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.leave import LeaveApplication, LeaveStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/leaves", tags=["Leave Applications"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


class LeaveApply(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=5, max_length=2000)


class LeaveReview(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    review_note: str | None = None


class LeaveResponse(BaseModel):
    id: int
    staff_id: int
    staff_name: str | None = None
    start_date: date
    end_date: date
    reason: str
    status: str
    reviewed_by_id: int | None = None
    review_note: str | None = None
    created_at: object

    model_config = {"from_attributes": True}


def _to_response(leave: LeaveApplication) -> LeaveResponse:
    response = LeaveResponse.model_validate(leave)
    if leave.staff:
        response.staff_name = f"{leave.staff.first_name} {leave.staff.last_name}"
    return response


@router.post("/", response_model=LeaveResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_leave(
    payload: LeaveApply,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
) -> LeaveResponse:
    """Teacher applies for leave (uses their linked staff record)."""
    if current_user.linked_staff_id is None:
        raise HTTPException(
            status_code=409, detail="Your login is not linked to a staff record"
        )
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="End date is before start date")

    leave = LeaveApplication(
        staff_id=current_user.linked_staff_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
    )
    db.add(leave)
    await db.flush()
    await db.refresh(leave)
    return _to_response(leave)


@router.get("/mine", response_model=List[LeaveResponse])
async def my_leaves(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
) -> List[LeaveResponse]:
    """The signed-in teacher's own leave history."""
    if current_user.linked_staff_id is None:
        return []
    result = await db.execute(
        select(LeaveApplication)
        .where(LeaveApplication.staff_id == current_user.linked_staff_id)
        .order_by(LeaveApplication.created_at.desc())
    )
    return [_to_response(l) for l in result.scalars().all()]


@router.get("/", response_model=List[LeaveResponse])
async def list_leaves(
    status_filter: str | None = Query(None, alias="status", pattern="^(pending|approved|rejected)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> List[LeaveResponse]:
    """All leave applications for admin review, newest first."""
    query = select(LeaveApplication)
    if status_filter:
        query = query.where(LeaveApplication.status == LeaveStatus(status_filter))
    query = query.order_by(LeaveApplication.created_at.desc())
    result = await db.execute(query)
    return [_to_response(l) for l in result.scalars().all()]


@router.put("/{leave_id}/review", response_model=LeaveResponse)
async def review_leave(
    leave_id: int,
    payload: LeaveReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> LeaveResponse:
    """Approve or reject a pending leave application."""
    leave = await db.get(LeaveApplication, leave_id)
    if leave is None:
        raise HTTPException(status_code=404, detail="Leave application not found")
    if leave.status != LeaveStatus.PENDING:
        raise HTTPException(status_code=409, detail="Already reviewed")

    leave.status = LeaveStatus(payload.status)
    leave.reviewed_by_id = current_user.id
    leave.review_note = payload.review_note
    await db.flush()
    await db.refresh(leave)
    return _to_response(leave)

"""Homework endpoints — post, list, submit, review."""

from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import require_role
from app.models.homework import Homework, HomeworkSubmission, SubmissionStatus
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.homework import (
    HomeworkCreate,
    HomeworkResponse,
    HomeworkSubmissionCreate,
    HomeworkSubmissionResponse,
)

router = APIRouter(prefix="/homework", tags=["Homework"])

TEACHER_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER)


@router.post("/", response_model=HomeworkResponse, status_code=status.HTTP_201_CREATED)
async def post_homework(
    payload: HomeworkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> HomeworkResponse:
    """Assign a new homework to a class/section."""
    assigned_by_id = current_user.linked_staff_id
    if not assigned_by_id:
        raise HTTPException(
            status_code=403,
            detail="User is not linked to a staff member",
        )

    hw = Homework(
        class_id=payload.class_id,
        section_id=payload.section_id,
        subject_id=payload.subject_id,
        assigned_by_id=assigned_by_id,
        title=payload.title,
        description=payload.description,
        attachment_url=payload.attachment_url,
        due_date=payload.due_date,
    )
    db.add(hw)
    await db.flush()
    await db.refresh(hw)
    return HomeworkResponse.model_validate(hw)


@router.get("/", response_model=List[HomeworkResponse])
async def list_homework(
    class_id: int | None = Query(None),
    section_id: int | None = Query(None),
    subject_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES, UserRole.STUDENT, UserRole.PARENT)),
) -> List[HomeworkResponse]:
    """List homework assignments with optional filters."""
    query = select(Homework)
    if class_id:
        query = query.where(Homework.class_id == class_id)
    if section_id:
        query = query.where(Homework.section_id == section_id)
    if subject_id:
        query = query.where(Homework.subject_id == subject_id)
    query = query.order_by(Homework.due_date.desc())

    result = await db.execute(query)
    return [HomeworkResponse.model_validate(h) for h in result.scalars().all()]


@router.post("/submit", response_model=HomeworkSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_homework(
    payload: HomeworkSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> HomeworkSubmissionResponse:
    """Submit homework as a student."""
    student_id = current_user.linked_student_id
    if not student_id:
        raise HTTPException(status_code=403, detail="User is not linked to a student")

    # Verify homework exists
    hw_result = await db.execute(
        select(Homework).where(Homework.id == payload.homework_id),
    )
    if not hw_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Homework not found")

    # Check for duplicate submission
    existing = await db.execute(
        select(HomeworkSubmission).where(
            HomeworkSubmission.homework_id == payload.homework_id,
            HomeworkSubmission.student_id == student_id,
        ),
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already submitted")

    submission = HomeworkSubmission(
        homework_id=payload.homework_id,
        student_id=student_id,
        submission_url=payload.submission_url,
        submitted_at=datetime.utcnow(),
        status=SubmissionStatus.SUBMITTED,
    )
    db.add(submission)
    await db.flush()
    await db.refresh(submission)
    return HomeworkSubmissionResponse.model_validate(submission)


@router.get("/{homework_id}/submissions", response_model=List[HomeworkSubmissionResponse])
async def list_submissions(
    homework_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> List[HomeworkSubmissionResponse]:
    """List all submissions for a homework assignment."""
    result = await db.execute(
        select(HomeworkSubmission).where(
            HomeworkSubmission.homework_id == homework_id,
        ).order_by(HomeworkSubmission.submitted_at),
    )
    return [HomeworkSubmissionResponse.model_validate(s) for s in result.scalars().all()]


@router.put("/submissions/{submission_id}/review", response_model=HomeworkSubmissionResponse)
async def review_submission(
    submission_id: int,
    remarks: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> HomeworkSubmissionResponse:
    """Mark a submission as reviewed with optional remarks."""
    result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id),
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.status = SubmissionStatus.REVIEWED
    submission.remarks = remarks
    await db.flush()
    await db.refresh(submission)
    return HomeworkSubmissionResponse.model_validate(submission)

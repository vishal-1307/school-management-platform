"""Staff CRUD endpoints with assignment management."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import require_role
from app.models.attendance import Attendance
from app.models.exam import Exam, ExamSubject, Mark
from app.models.homework import Homework, HomeworkSubmission, SubmissionStatus
from app.models.notice import Notice, NoticeAudience
from app.models.staff import Staff, StaffSubjectAssignment
from app.models.student import Student
from app.models.timetable import TimetableSlot
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.dashboard import (
    AttendanceStatusSummary,
    ClassSectionRef,
    DashboardNotice,
    MyClassChip,
    PendingMarksRow,
    TeacherDashboardResponse,
    TimetablePeriod,
)
from app.schemas.staff import StaffCreate, StaffResponse, StaffSubjectAssignmentSchema, StaffUpdate
from app.services.schedule import current_period_number, today_day_name

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


@router.get("/me/dashboard", response_model=TeacherDashboardResponse)
async def get_my_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
) -> TeacherDashboardResponse:
    """Everything the teacher dashboard needs, in one request (SRS 7.1)."""
    if current_user.linked_staff_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a staff record")
    staff_id = current_user.linked_staff_id

    assignments_result = await db.execute(
        select(StaffSubjectAssignment)
        .options(
            selectinload(StaffSubjectAssignment.subject),
            selectinload(StaffSubjectAssignment.class_),
            selectinload(StaffSubjectAssignment.section),
        )
        .where(StaffSubjectAssignment.staff_id == staff_id)
    )
    assignments = assignments_result.scalars().all()

    # ── Today's schedule ─────────────────────────────────────────────────
    day = today_day_name()
    slots_result = await db.execute(
        select(TimetableSlot)
        .where(TimetableSlot.staff_id == staff_id, TimetableSlot.day_of_week == day)
        .order_by(TimetableSlot.period_number)
    )
    now_period = current_period_number()
    today_schedule = [
        TimetablePeriod(
            period_number=slot.period_number,
            subject_name=slot.subject.name if slot.subject else "",
            subtitle=f"{slot.class_.name} {slot.section.name}" if slot.class_ and slot.section else "",
            is_current=(slot.period_number == now_period),
        )
        for slot in slots_result.scalars().all()
    ]

    # ── Attendance-marked-today, per distinct assigned class/section ───
    pairs = {(a.class_id, a.section_id) for a in assignments}
    today_date = datetime.utcnow().date()
    pending_pairs: list[ClassSectionRef] = []
    for class_id, section_id in pairs:
        total_result = await db.execute(
            select(func.count(Student.id)).where(
                Student.class_id == class_id, Student.section_id == section_id, Student.is_active
            )
        )
        total_students = total_result.scalar() or 0
        marked_result = await db.execute(
            select(func.count(func.distinct(Attendance.student_id)))
            .select_from(Attendance)
            .join(Student, Student.id == Attendance.student_id)
            .where(
                Student.class_id == class_id,
                Student.section_id == section_id,
                Attendance.date == today_date,
            )
        )
        marked = marked_result.scalar() or 0
        if total_students > 0 and marked < total_students:
            match = next(
                (a for a in assignments if a.class_id == class_id and a.section_id == section_id),
                None,
            )
            if match:
                pending_pairs.append(
                    ClassSectionRef(
                        class_id=class_id, section_id=section_id,
                        class_name=match.class_.name if match.class_ else "",
                        section_name=match.section.name if match.section else "",
                    )
                )
    attendance_status = AttendanceStatusSummary(
        all_marked=(len(pending_pairs) == 0), pending=pending_pairs
    )

    # ── Homework submissions awaiting review (own assignments only) ────
    hw_ids_result = await db.execute(
        select(Homework.id).where(Homework.assigned_by_id == staff_id)
    )
    my_homework_ids = [row[0] for row in hw_ids_result.all()]
    homework_to_review_count = 0
    if my_homework_ids:
        review_count_result = await db.execute(
            select(func.count(HomeworkSubmission.id)).where(
                HomeworkSubmission.homework_id.in_(my_homework_ids),
                HomeworkSubmission.status == SubmissionStatus.SUBMITTED,
            )
        )
        homework_to_review_count = review_count_result.scalar() or 0

    # ── My classes (deduped subject/class/section chips) ───────────────
    my_classes = [
        MyClassChip(
            class_name=a.class_.name if a.class_ else "",
            section_name=a.section.name if a.section else "",
            subject_name=a.subject.name if a.subject else "",
        )
        for a in assignments
    ]

    # ── Latest notice visible to staff ──────────────────────────────────
    notice_result = await db.execute(
        select(Notice)
        .where(
            Notice.published_at.is_not(None),
            (Notice.audience == NoticeAudience.EVERYONE)
            | (Notice.audience == NoticeAudience.STAFF),
        )
        .order_by(Notice.published_at.desc())
        .limit(1)
    )
    latest = notice_result.scalar_one_or_none()
    latest_notice = (
        DashboardNotice(id=latest.id, title=latest.title, published_at=latest.published_at)
        if latest else None
    )

    # ── Pending marks entry: my subject/class exam-subjects, unlocked,
    #    with fewer marks entered than active students in that class ────
    pending_marks: list[PendingMarksRow] = []
    seen_subject_class = {(a.subject_id, a.class_id) for a in assignments}
    for subject_id, class_id in seen_subject_class:
        es_result = await db.execute(
            select(ExamSubject)
            .options(selectinload(ExamSubject.exam), selectinload(ExamSubject.subject))
            .join(Exam, Exam.id == ExamSubject.exam_id)
            .where(
                ExamSubject.subject_id == subject_id,
                Exam.class_id == class_id,
                Exam.is_locked.is_(False),
            )
        )
        for es in es_result.scalars().all():
            total_result = await db.execute(
                select(func.count(Student.id)).where(
                    Student.class_id == class_id, Student.is_active
                )
            )
            total_students = total_result.scalar() or 0
            entered_result = await db.execute(
                select(func.count(Mark.id)).where(
                    Mark.exam_subject_id == es.id, Mark.marks_obtained.is_not(None)
                )
            )
            entered_count = entered_result.scalar() or 0
            if total_students > 0 and entered_count < total_students:
                pending_marks.append(
                    PendingMarksRow(
                        exam_id=es.exam_id,
                        exam_subject_id=es.id,
                        exam_name=es.exam.name if es.exam else "",
                        subject_name=es.subject.name if es.subject else "",
                        class_name=es.exam.class_.name if es.exam and es.exam.class_ else "",
                        entered_count=entered_count,
                        total_students=total_students,
                    )
                )

    return TeacherDashboardResponse(
        today_schedule=today_schedule,
        attendance_status=attendance_status,
        homework_to_review_count=homework_to_review_count,
        my_classes=my_classes,
        latest_notice=latest_notice,
        pending_marks=pending_marks,
        generated_at=datetime.now(timezone.utc),
    )


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

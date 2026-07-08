"""Exam management endpoints — CRUD, marks entry, lock/unlock, report cards."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import require_role
from app.models.academic import Class, Subject
from app.models.exam import Exam, ExamSubject, Mark
from app.models.student import Student
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.exam import (
    ExamCreate,
    MarksEntryRequest,
    ReportCardResponse,
    SubjectMarkResponse,
)
from app.services.scoping import require_subject_class_scope

router = APIRouter(prefix="/exams", tags=["Exams"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)
TEACHER_ROLES = (*ADMIN_ROLES, UserRole.TEACHER)


# ── Exam CRUD ────────────────────────────────────────────────────────────


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> dict:
    """Create a new exam with its subject configuration."""
    if payload.start_date > payload.end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")

    exam = Exam(
        name=payload.name,
        academic_year_id=payload.academic_year_id,
        class_id=payload.class_id,
        exam_type=payload.exam_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    db.add(exam)
    await db.flush()

    for s in payload.subjects:
        db.add(ExamSubject(
            exam_id=exam.id,
            subject_id=s.subject_id,
            max_marks=s.max_marks,
            passing_marks=s.passing_marks,
            exam_date=s.exam_date,
        ))

    await db.flush()
    await db.refresh(exam, attribute_names=["exam_subjects"])
    return {"id": exam.id, "name": exam.name, "subjects_count": len(exam.exam_subjects)}


@router.get("/", response_model=List[dict])
async def list_exams(
    academic_year_id: int | None = Query(None),
    class_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> List[dict]:
    """List exams with optional filters."""
    query = select(Exam).options(selectinload(Exam.exam_subjects))
    if academic_year_id:
        query = query.where(Exam.academic_year_id == academic_year_id)
    if class_id:
        query = query.where(Exam.class_id == class_id)
    query = query.order_by(Exam.start_date.desc())

    result = await db.execute(query)
    exams = result.scalars().all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "exam_type": e.exam_type,
            "class_id": e.class_id,
            "start_date": e.start_date.isoformat(),
            "end_date": e.end_date.isoformat(),
            "is_locked": e.is_locked,
            "results_published": e.results_published,
            "subjects_count": len(e.exam_subjects),
        }
        for e in exams
    ]


@router.get("/my-results", response_model=List[dict])
async def my_published_results(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> List[dict]:
    """Published exams for the signed-in student's class (SRS 8.4)."""
    if current_user.linked_student_id is None:
        return []
    student = await db.get(Student, current_user.linked_student_id)
    if student is None:
        return []
    result = await db.execute(
        select(Exam)
        .where(Exam.class_id == student.class_id, Exam.results_published)
        .order_by(Exam.start_date.desc())
    )
    return [
        {
            "id": e.id,
            "name": e.name,
            "exam_type": e.exam_type,
            "start_date": e.start_date.isoformat(),
            "student_id": student.id,
        }
        for e in result.scalars().all()
    ]


@router.get("/marks", response_model=List[dict])
async def list_marks(
    exam_subject_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> List[dict]:
    """Marks already entered for an exam subject (for review/edit grids)."""
    es_result = await db.execute(
        select(ExamSubject).options(selectinload(ExamSubject.exam)).where(
            ExamSubject.id == exam_subject_id
        )
    )
    exam_subject = es_result.scalar_one_or_none()
    if not exam_subject:
        raise HTTPException(status_code=404, detail="Exam subject not found")
    await require_subject_class_scope(
        db, current_user, exam_subject.subject_id, exam_subject.exam.class_id
    )

    result = await db.execute(
        select(Mark).where(Mark.exam_subject_id == exam_subject_id).order_by(Mark.student_id)
    )
    return [
        {
            "student_id": m.student_id,
            "marks_obtained": m.marks_obtained,
            "grade": m.grade,
            "is_submitted": m.is_submitted,
        }
        for m in result.scalars().all()
    ]


@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> dict:
    """Get exam details with subjects."""
    result = await db.execute(
        select(Exam).options(
            selectinload(Exam.exam_subjects).selectinload(ExamSubject.subject),
        ).where(Exam.id == exam_id),
    )
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    return {
        "id": exam.id,
        "name": exam.name,
        "exam_type": exam.exam_type,
        "class_id": exam.class_id,
        "academic_year_id": exam.academic_year_id,
        "start_date": exam.start_date.isoformat(),
        "end_date": exam.end_date.isoformat(),
        "is_locked": exam.is_locked,
        "results_published": exam.results_published,
        "subjects": [
            {
                "id": es.id,
                "subject_id": es.subject_id,
                "subject_name": es.subject.name if es.subject else "",
                "max_marks": es.max_marks,
                "passing_marks": es.passing_marks,
                "exam_date": es.exam_date.isoformat() if es.exam_date else None,
            }
            for es in exam.exam_subjects
        ],
    }


@router.delete("/{exam_id}", response_model=MessageResponse)
async def delete_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Delete an exam and all its subjects/marks (cascade)."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.is_locked:
        raise HTTPException(status_code=409, detail="Cannot delete a locked exam")

    await db.delete(exam)
    await db.flush()
    return MessageResponse(message=f"Exam '{exam.name}' deleted")


# ── Marks Entry ──────────────────────────────────────────────────────────


@router.post("/marks", response_model=MessageResponse)
async def enter_marks(
    payload: MarksEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES)),
) -> MessageResponse:
    """Bulk-enter marks for an exam-subject."""
    # Verify exam subject exists and exam is not locked
    es_result = await db.execute(
        select(ExamSubject).options(selectinload(ExamSubject.exam)).where(
            ExamSubject.id == payload.exam_subject_id,
        ),
    )
    exam_subject = es_result.scalar_one_or_none()
    if not exam_subject:
        raise HTTPException(status_code=404, detail="Exam subject not found")
    if exam_subject.exam.is_locked:
        raise HTTPException(status_code=409, detail="Exam is locked — marks cannot be edited")

    await require_subject_class_scope(
        db, current_user, exam_subject.subject_id, exam_subject.exam.class_id
    )

    entered = 0
    for entry in payload.entries:
        # Validate marks
        if entry.marks_obtained is not None and entry.marks_obtained > exam_subject.max_marks:
            raise HTTPException(
                status_code=422,
                detail=f"Student {entry.student_id}: marks {entry.marks_obtained} exceed max {exam_subject.max_marks}",
            )

        # Upsert
        existing_result = await db.execute(
            select(Mark).where(
                Mark.exam_subject_id == payload.exam_subject_id,
                Mark.student_id == entry.student_id,
            ),
        )
        existing = existing_result.scalar_one_or_none()

        grade = entry.grade
        if not grade and entry.marks_obtained is not None:
            pct = (entry.marks_obtained / exam_subject.max_marks) * 100
            if pct >= 90:
                grade = "A+"
            elif pct >= 80:
                grade = "A"
            elif pct >= 70:
                grade = "B+"
            elif pct >= 60:
                grade = "B"
            elif pct >= 50:
                grade = "C"
            elif pct >= 40:
                grade = "D"
            else:
                grade = "F"

        if existing:
            existing.marks_obtained = entry.marks_obtained
            existing.grade = grade
            existing.entered_by_id = current_user.id
        else:
            db.add(Mark(
                exam_subject_id=payload.exam_subject_id,
                student_id=entry.student_id,
                marks_obtained=entry.marks_obtained,
                grade=grade,
                entered_by_id=current_user.id,
            ))
        entered += 1

    await db.flush()
    return MessageResponse(message=f"{entered} marks entered/updated")


# ── Lock / Unlock ────────────────────────────────────────────────────────


@router.post("/{exam_id}/lock", response_model=MessageResponse)
async def lock_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Lock an exam to prevent further marks editing."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    exam.is_locked = True
    await db.flush()
    return MessageResponse(message=f"Exam '{exam.name}' locked")


@router.post("/{exam_id}/unlock", response_model=MessageResponse)
async def unlock_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Unlock an exam (super admin only)."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    exam.is_locked = False
    await db.flush()
    return MessageResponse(message=f"Exam '{exam.name}' unlocked")


@router.post("/{exam_id}/publish", response_model=MessageResponse)
async def publish_results(
    exam_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> MessageResponse:
    """Publish exam results to students and parents."""
    result = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if not exam.is_locked:
        raise HTTPException(status_code=409, detail="Exam must be locked before publishing")

    exam.results_published = True
    await db.flush()

    from app.services.automations import notify_results_published

    background_tasks.add_task(notify_results_published, exam_id)
    return MessageResponse(message=f"Results for '{exam.name}' published")


@router.get("/{exam_id}/marks/export.csv")
async def export_exam_marks_csv(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """All marks for an exam as CSV — one row per student, one column per subject."""
    import csv
    import io

    from fastapi.responses import StreamingResponse

    exam_result = await db.execute(
        select(Exam).options(
            selectinload(Exam.exam_subjects).selectinload(ExamSubject.subject),
            selectinload(Exam.exam_subjects).selectinload(ExamSubject.marks),
        ).where(Exam.id == exam_id),
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    students = (
        await db.execute(
            select(Student)
            .where(Student.class_id == exam.class_id, Student.is_active)
            .order_by(Student.roll_number)
        )
    ).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    subject_names = [es.subject.name if es.subject else str(es.subject_id) for es in exam.exam_subjects]
    writer.writerow(["roll_number", "student", "admission_number", *subject_names, "total"])
    for student in students:
        row = [student.roll_number or "", f"{student.first_name} {student.last_name}", student.admission_number]
        total = 0.0
        for es in exam.exam_subjects:
            mark = next((m for m in es.marks if m.student_id == student.id), None)
            value = mark.marks_obtained if mark and mark.marks_obtained is not None else ""
            if isinstance(value, float):
                total += value
            row.append(value)
        row.append(total)
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=marks-exam-{exam_id}.csv"},
    )


# ── Report Card ──────────────────────────────────────────────────────────


@router.get("/{exam_id}/report-card/{student_id}", response_model=ReportCardResponse)
async def get_report_card(
    exam_id: int,
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*TEACHER_ROLES, UserRole.STUDENT, UserRole.PARENT)),
) -> ReportCardResponse:
    """Generate a report card for a student in a specific exam.

    Students/parents may only open their own linked student's card, and
    only after the admin publishes results (FR-16).
    """
    # Fetch exam with subjects
    exam_result = await db.execute(
        select(Exam).options(
            selectinload(Exam.exam_subjects).selectinload(ExamSubject.subject),
            selectinload(Exam.exam_subjects).selectinload(ExamSubject.marks),
        ).where(Exam.id == exam_id),
    )
    exam = exam_result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role in (UserRole.STUDENT, UserRole.PARENT):
        if current_user.linked_student_id != student_id:
            raise HTTPException(status_code=403, detail="Not your report card")
        if not exam.results_published:
            raise HTTPException(
                status_code=403, detail="Results have not been published yet"
            )

    # Fetch student
    student_result = await db.execute(select(Student).where(Student.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Fetch class name
    class_result = await db.execute(select(Class).where(Class.id == student.class_id))
    class_obj = class_result.scalar_one_or_none()

    subjects: list[SubjectMarkResponse] = []
    total_marks = 0.0
    total_obtained = 0.0
    all_passed = True

    for es in exam.exam_subjects:
        student_mark = next((m for m in es.marks if m.student_id == student_id), None)
        obtained = student_mark.marks_obtained if student_mark and student_mark.marks_obtained is not None else 0.0
        grade = student_mark.grade if student_mark else "N/A"
        passed = obtained >= es.passing_marks

        if not passed:
            all_passed = False

        subjects.append(SubjectMarkResponse(
            subject_name=es.subject.name if es.subject else "Unknown",
            subject_code=es.subject.code if es.subject else "",
            max_marks=es.max_marks,
            passing_marks=es.passing_marks,
            marks_obtained=obtained,
            grade=grade,
            passed=passed,
        ))
        total_marks += es.max_marks
        total_obtained += obtained

    percentage = round((total_obtained / total_marks * 100), 2) if total_marks > 0 else 0.0

    if percentage >= 90:
        overall_grade = "A+"
    elif percentage >= 80:
        overall_grade = "A"
    elif percentage >= 70:
        overall_grade = "B+"
    elif percentage >= 60:
        overall_grade = "B"
    elif percentage >= 50:
        overall_grade = "C"
    elif percentage >= 40:
        overall_grade = "D"
    else:
        overall_grade = "F"

    return ReportCardResponse(
        student_id=student.id,
        student_name=f"{student.first_name} {student.last_name}",
        admission_number=student.admission_number,
        class_name=class_obj.name if class_obj else str(student.class_id),
        exam_name=exam.name,
        subjects=subjects,
        total_marks=total_marks,
        total_obtained=total_obtained,
        percentage=percentage,
        overall_grade=overall_grade,
        result="Pass" if all_passed else "Fail",
    )

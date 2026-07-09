"""Student CRUD endpoints with bulk import and TC generation."""

from __future__ import annotations

import math
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import require_role
from app.models.academic import Section
from app.models.attendance import Attendance, AttendanceStatus
from app.models.exam import Exam, ExamSubject, Mark
from app.models.fee import FeeStructure, FeeTransaction
from app.models.homework import Homework, HomeworkSubmission
from app.models.notice import Notice, NoticeAudience
from app.models.school import School
from app.models.student import Parent, Student
from app.models.timetable import TimetableSlot
from app.models.user import User, UserRole
from app.schemas.common import MessageResponse
from app.schemas.dashboard import (
    DashboardNotice,
    LatestResult,
    StudentDashboardResponse,
    TimetablePeriod,
)
from app.schemas.student import (
    BulkImportResponse,
    PromoteClassRequest,
    PromoteClassResponse,
    StudentCreate,
    StudentListResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services.certificates import generate_tc
from app.services.schedule import current_period_number, today_day_name

router = APIRouter(prefix="/students", tags=["Students"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)
STAFF_ROLES = (*ADMIN_ROLES, UserRole.TEACHER)


async def _generate_admission_number(db: AsyncSession) -> str:
    """Generate a sequential admission number like ADM-00001."""
    result = await db.execute(select(func.count(Student.id)))
    count = result.scalar() or 0
    return f"ADM-{count + 1:05d}"


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StudentResponse:
    """Create a new student with optional parent records."""
    admission_number = await _generate_admission_number(db)

    student = Student(
        admission_number=admission_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        dob=payload.dob,
        gender=payload.gender,
        photo_url=payload.photo_url,
        class_id=payload.class_id,
        section_id=payload.section_id,
        roll_number=payload.roll_number,
        address=payload.address,
        documents=payload.documents,
    )
    db.add(student)
    await db.flush()

    for p in payload.parents:
        parent = Parent(
            name=p.name,
            phone=p.phone,
            email=p.email,
            whatsapp_number=p.whatsapp_number,
            relation=p.relation,
            student_id=student.id,
        )
        db.add(parent)

    await db.flush()
    await db.refresh(student, attribute_names=["parents"])
    return StudentResponse.model_validate(student)


@router.get("/", response_model=StudentListResponse)
async def list_students(
    class_id: int | None = Query(None),
    section_id: int | None = Query(None),
    is_active: bool = Query(True),
    search: str | None = Query(None, description="Search by name or admission number"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*STAFF_ROLES)),
) -> StudentListResponse:
    """List students with filters, search, and pagination.

    Teachers are restricted to classes they are assigned to — otherwise
    any teacher could browse the entire school's students, including
    parent phone numbers and addresses.
    """
    query = select(Student).options(selectinload(Student.parents))
    count_query = select(func.count(Student.id))

    filters = [Student.is_active == is_active]

    if current_user.role == UserRole.TEACHER:
        from app.services.scoping import teacher_assigned_class_ids

        assigned = await teacher_assigned_class_ids(db, current_user.linked_staff_id or -1)
        if class_id is not None and class_id not in assigned:
            raise HTTPException(
                status_code=403, detail="You are not assigned to this class"
            )
        filters.append(Student.class_id.in_(assigned or {-1}))

    if class_id:
        filters.append(Student.class_id == class_id)
    if section_id:
        filters.append(Student.section_id == section_id)
    if search:
        pattern = f"%{search}%"
        filters.append(
            (Student.first_name.ilike(pattern))
            | (Student.last_name.ilike(pattern))
            | (Student.admission_number.ilike(pattern))
        )

    for f in filters:
        query = query.where(f)
        count_query = count_query.where(f)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = math.ceil(total / page_size) if total else 0

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Student.id)
    result = await db.execute(query)
    students = result.scalars().all()

    return StudentListResponse(
        items=[StudentResponse.model_validate(s) for s in students],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/export.csv")
async def export_students_csv(
    class_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StreamingResponse:
    """Download the student register as CSV (opens in Excel)."""
    import csv
    import io

    query = select(Student).options(selectinload(Student.parents)).where(Student.is_active)
    if class_id:
        query = query.where(Student.class_id == class_id)
    result = await db.execute(query.order_by(Student.class_id, Student.roll_number))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["admission_number", "first_name", "last_name", "dob", "gender", "class_id",
         "section_id", "roll_number", "address", "parent_name", "parent_phone", "relation"]
    )
    for s in result.scalars().all():
        parent = s.parents[0] if s.parents else None
        writer.writerow(
            [s.admission_number, s.first_name, s.last_name, s.dob.isoformat(), s.gender,
             s.class_id, s.section_id, s.roll_number or "", s.address or "",
             parent.name if parent else "", parent.phone if parent else "",
             parent.relation if parent else ""]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"},
    )


@router.get("/me", response_model=StudentResponse)
async def get_my_student_record(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> StudentResponse:
    """The signed-in student's own record (SRS 8.8)."""
    if current_user.linked_student_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a student record")
    result = await db.execute(
        select(Student)
        .options(selectinload(Student.parents))
        .where(Student.id == current_user.linked_student_id),
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student record not found")
    return StudentResponse.model_validate(student)


@router.get("/me/dashboard", response_model=StudentDashboardResponse)
async def get_my_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT, UserRole.PARENT)),
) -> StudentDashboardResponse:
    """Everything the student dashboard needs, in one request (SRS 8.1)."""
    if current_user.linked_student_id is None:
        raise HTTPException(status_code=409, detail="Your login is not linked to a student record")

    student = await db.get(Student, current_user.linked_student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student record not found")

    # ── Attendance percentage ───────────────────────────────────────────
    att_result = await db.execute(
        select(Attendance.status).where(Attendance.student_id == student.id)
    )
    statuses = [row[0] for row in att_result.all()]
    total = len(statuses)
    present = sum(1 for s in statuses if s in (AttendanceStatus.PRESENT, AttendanceStatus.LATE))
    attendance_percentage = round(present / total * 100, 1) if total else None

    # ── Pending homework: assigned to my class/section, not yet submitted
    hw_result = await db.execute(
        select(Homework.id).where(
            Homework.class_id == student.class_id, Homework.section_id == student.section_id
        )
    )
    homework_ids = {row[0] for row in hw_result.all()}
    submitted_result = await db.execute(
        select(HomeworkSubmission.homework_id).where(
            HomeworkSubmission.student_id == student.id,
            HomeworkSubmission.homework_id.in_(homework_ids) if homework_ids else False,
        )
    )
    submitted_ids = {row[0] for row in submitted_result.all()}
    pending_homework_count = len(homework_ids - submitted_ids)

    # ── Latest published result (FR-16: never surface an unpublished exam)
    latest_result: LatestResult | None = None
    exam_result = await db.execute(
        select(Exam)
        .where(Exam.class_id == student.class_id, Exam.results_published.is_(True))
        .order_by(Exam.start_date.desc())
        .limit(1)
    )
    latest_exam = exam_result.scalar_one_or_none()
    if latest_exam:
        es_result = await db.execute(
            select(ExamSubject).where(ExamSubject.exam_id == latest_exam.id)
        )
        exam_subjects = es_result.scalars().all()
        total_max = sum(es.max_marks for es in exam_subjects)
        marks_result = await db.execute(
            select(Mark).where(
                Mark.student_id == student.id,
                Mark.exam_subject_id.in_([es.id for es in exam_subjects]),
            )
        )
        obtained = sum(m.marks_obtained or 0 for m in marks_result.scalars().all())
        percentage = round(obtained / total_max * 100, 1) if total_max else None
        grade = None
        if percentage is not None:
            grade = (
                "A+" if percentage >= 90 else "A" if percentage >= 80 else "B+" if percentage >= 70
                else "B" if percentage >= 60 else "C" if percentage >= 50 else "D" if percentage >= 40
                else "F"
            )
        latest_result = LatestResult(
            exam_name=latest_exam.name, published=True, percentage=percentage, grade=grade
        )

    # ── Fee due: outstanding balance across every structure for my class
    structures_result = await db.execute(
        select(FeeStructure).where(FeeStructure.class_id == student.class_id)
    )
    structures = structures_result.scalars().all()
    fee_due = 0.0
    for structure in structures:
        paid_result = await db.execute(
            select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0)).where(
                FeeTransaction.student_id == student.id,
                FeeTransaction.fee_structure_id == structure.id,
            )
        )
        paid = float(paid_result.scalar() or 0)
        fee_due += max(0.0, structure.amount - paid)

    # ── Today's timetable ───────────────────────────────────────────────
    day = today_day_name()
    slots_result = await db.execute(
        select(TimetableSlot)
        .where(
            TimetableSlot.class_id == student.class_id,
            TimetableSlot.section_id == student.section_id,
            TimetableSlot.day_of_week == day,
        )
        .order_by(TimetableSlot.period_number)
    )
    now_period = current_period_number()
    today_timetable = [
        TimetablePeriod(
            period_number=slot.period_number,
            subject_name=slot.subject.name if slot.subject else "",
            subtitle=f"{slot.staff.first_name} {slot.staff.last_name}" if slot.staff else "",
            is_current=(slot.period_number == now_period),
        )
        for slot in slots_result.scalars().all()
    ]

    # ── Recent notices: everyone, or targeted at my class ───────────────
    notices_result = await db.execute(
        select(Notice)
        .where(
            Notice.published_at.is_not(None),
            (Notice.audience == NoticeAudience.EVERYONE)
            | (
                (Notice.audience == NoticeAudience.CLASS)
                & (Notice.target_class_id == student.class_id)
            ),
        )
        .order_by(Notice.published_at.desc())
        .limit(5)
    )
    recent_notices = [
        DashboardNotice(id=n.id, title=n.title, published_at=n.published_at)
        for n in notices_result.scalars().all()
    ]

    return StudentDashboardResponse(
        attendance_percentage=attendance_percentage,
        pending_homework_count=pending_homework_count,
        latest_result=latest_result,
        fee_due=round(fee_due, 2),
        today_timetable=today_timetable,
        recent_notices=recent_notices,
        generated_at=datetime.utcnow(),
    )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*STAFF_ROLES)),
) -> StudentResponse:
    """Get a single student by ID (teachers: only their assigned classes)."""
    result = await db.execute(
        select(Student).options(selectinload(Student.parents)).where(Student.id == student_id),
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user.role == UserRole.TEACHER:
        from app.services.scoping import teacher_assigned_class_ids

        assigned = await teacher_assigned_class_ids(db, current_user.linked_staff_id or -1)
        if student.class_id not in assigned:
            raise HTTPException(status_code=403, detail="You are not assigned to this student's class")

    return StudentResponse.model_validate(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> StudentResponse:
    """Update a student's details (partial update)."""
    result = await db.execute(
        select(Student).options(selectinload(Student.parents)).where(Student.id == student_id),
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    await db.flush()
    await db.refresh(student)
    return StudentResponse.model_validate(student)


@router.delete("/{student_id}", response_model=MessageResponse)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    """Soft-delete a student by setting is_active=False."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.is_active = False
    await db.flush()
    return MessageResponse(message=f"Student {student.admission_number} deactivated")


@router.post("/bulk-import", response_model=BulkImportResponse)
async def bulk_import_students(
    students: List[StudentCreate],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> BulkImportResponse:
    """Import multiple students in a single request."""
    imported = 0
    skipped = 0
    errors: List[str] = []

    for idx, payload in enumerate(students):
        try:
            admission_number = await _generate_admission_number(db)
            student = Student(
                admission_number=admission_number,
                first_name=payload.first_name,
                last_name=payload.last_name,
                dob=payload.dob,
                gender=payload.gender,
                photo_url=payload.photo_url,
                class_id=payload.class_id,
                section_id=payload.section_id,
                roll_number=payload.roll_number,
                address=payload.address,
                documents=payload.documents,
            )
            db.add(student)
            await db.flush()

            for p in payload.parents:
                db.add(Parent(
                    name=p.name,
                    phone=p.phone,
                    email=p.email,
                    whatsapp_number=p.whatsapp_number,
                    relation=p.relation,
                    student_id=student.id,
                ))
            imported += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"Row {idx + 1}: {exc}")

    await db.flush()
    return BulkImportResponse(imported=imported, skipped=skipped, errors=errors)


@router.post("/promote", response_model=PromoteClassResponse)
async def promote_class(
    payload: PromoteClassRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> PromoteClassResponse:
    """Move every active student of a class to the next class in one action (SRS 6.2)."""
    if payload.from_class_id == payload.to_class_id:
        raise HTTPException(status_code=400, detail="Source and target class are the same")

    section = await db.get(Section, payload.to_section_id)
    if section is None or section.class_id != payload.to_class_id:
        raise HTTPException(
            status_code=400, detail="Target section does not belong to the target class"
        )

    result = await db.execute(
        select(Student).where(
            Student.class_id == payload.from_class_id, Student.is_active
        )
    )
    students = result.scalars().all()
    for student in students:
        student.class_id = payload.to_class_id
        student.section_id = payload.to_section_id

    from app.routers.users import log_action

    await log_action(
        db,
        current_user,
        "students.promote_class",
        "class",
        payload.from_class_id,
        {"to_class_id": payload.to_class_id, "count": len(students)},
    )
    return PromoteClassResponse(promoted=len(students))


@router.get("/{student_id}/tc", response_class=HTMLResponse)
async def generate_transfer_certificate(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> HTMLResponse:
    """Generate a Transfer Certificate for the student as HTML."""
    result = await db.execute(
        select(Student).options(selectinload(Student.parents)).where(Student.id == student_id),
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Fetch school info
    school_result = await db.execute(select(School).limit(1))
    school = school_result.scalar_one_or_none()
    school_data = {
        "name": school.name if school else "School Name",
        "address": school.address if school else "",
        "affiliation_number": school.affiliation_number if school else "",
    }

    father = next((p for p in student.parents if p.relation == "father"), None)
    student_data = {
        "name": f"{student.first_name} {student.last_name}",
        "admission_number": student.admission_number,
        "class_name": str(student.class_id),
        "dob": student.dob.isoformat(),
        "father_name": father.name if father else "N/A",
        "join_date": student.created_at.strftime("%Y-%m-%d"),
        "leave_date": datetime.utcnow().strftime("%Y-%m-%d"),
    }

    html = await generate_tc(student_data, school_data)
    return HTMLResponse(content=html)


@router.get("/{student_id}/bonafide", response_class=HTMLResponse)
async def generate_bonafide_certificate(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> HTMLResponse:
    """Printable Bonafide Certificate pre-filled from the student record (FR-6)."""
    from app.services.certificates import generate_bonafide

    result = await db.execute(
        select(Student).options(selectinload(Student.parents)).where(Student.id == student_id),
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    school_result = await db.execute(select(School).limit(1))
    school = school_result.scalar_one_or_none()
    school_data = {
        "name": school.name if school else "School Name",
        "address": school.address if school else "",
        "affiliation_number": school.affiliation_number if school else "",
    }

    father = next((p for p in student.parents if p.relation == "father"), None)
    student_data = {
        "name": f"{student.first_name} {student.last_name}",
        "admission_number": student.admission_number,
        "class_name": str(student.class_id),
        "dob": student.dob.isoformat(),
        "father_name": father.name if father else "N/A",
    }

    html = await generate_bonafide(student_data, school_data)
    return HTMLResponse(content=html)

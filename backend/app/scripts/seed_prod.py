"""Idempotent demo seed — safe to run on every boot.

Two layers:
1. Bootstrap (always runs, per-item idempotent): school profile, current
   academic year, classes Nursery..Class 12 + one section each, core
   subjects, a super_admin login. Safe to re-run indefinitely.
2. Demo walkthrough data (runs ONCE — skipped entirely once the 'admin'
   login exists): teachers, students across two classes/three sections,
   attendance history, homework with submissions, exams (one published,
   one not — proves FR-16 hides unpublished results), fee structures with
   paid/partial/defaulter students, targeted notices, a full timetable,
   staged admission enquiries, and contact messages — enough to click
   through every page of every portal and see real data.

Credentials are also written to DEMO_CREDENTIALS.md (repo root) — see
that file for the full table and the wipe procedure before real data.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.database import async_session_factory
from app.models.academic import AcademicYear, Class, Section, Subject
from app.models.admission import AdmissionEnquiry, EnquiryStatus
from app.models.attendance import Attendance, AttendanceStatus
from app.models.contact import ContactMessage
from app.models.exam import Exam, ExamSubject, Mark
from app.models.fee import FeeStructure, FeeTransaction, PaymentMode
from app.models.homework import Homework, HomeworkSubmission, SubmissionStatus
from app.models.notice import Notice, NoticeAudience
from app.models.school import School
from app.models.staff import Staff, StaffSubjectAssignment
from app.models.student import Parent, Student
from app.models.timetable import TimetableSlot
from app.models.user import User, UserRole

CLASS_NAMES = ["Nursery", "LKG", "UKG"] + [f"Class {n}" for n in range(1, 13)]

SUBJECTS = [
    ("English", "ENG101"),
    ("Hindi", "HIN101"),
    ("Mathematics", "MAT101"),
    ("Environmental Studies", "EVS101"),
    ("Science", "SCI101"),
    ("Social Science", "SST101"),
    ("Computer Science", "CSC101"),
    ("General Knowledge", "GKN101"),
    ("Art & Craft", "ART101"),
    ("Physical Education", "PED101"),
]

ADMIN_PASSWORD = "Admin@2026"
TEACHER_PASSWORD = "Teach@2026"
STUDENT_PASSWORD = "Study@2026"


def _recent_weekdays(count: int, before: date) -> list[date]:
    """The most recent `count` Mon-Sat dates strictly before `before`."""
    days: list[date] = []
    cursor = before - timedelta(days=1)
    while len(days) < count:
        if cursor.weekday() != 6:  # skip Sunday
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


async def seed_production() -> None:
    async with async_session_factory() as session:
        created: list[str] = []

        # ── Layer 1: bootstrap (always safe to re-run) ──────────────────
        school = (await session.execute(select(School))).scalars().first()
        if school is None:
            session.add(
                School(
                    name="Knowledge Development Kindergarten Academy",
                    address="Sector 5, Knowledge Campus, Near City Park, New Delhi, 110001",
                    affiliation_number="1234567",
                    contact_email="info@knowledgeacademy.edu.in",
                    contact_phone="+91 98765 43210",
                    settings={"allow_online_fees": True, "automation": {}},
                )
            )
            created.append("school")

        year = (
            await session.execute(select(AcademicYear).where(AcademicYear.is_current))
        ).scalars().first()
        if year is None:
            year = AcademicYear(
                label="2026-27",
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                is_current=True,
            )
            session.add(year)
            await session.flush()
            created.append("academic year 2026-27")

        existing_classes = {
            c.name: c for c in (await session.execute(select(Class))).scalars().all()
        }
        for order, name in enumerate(CLASS_NAMES, start=1):
            if name not in existing_classes:
                cls = Class(name=name, numeric_order=order)
                session.add(cls)
                await session.flush()
                session.add(Section(name="A", class_id=cls.id))
                existing_classes[name] = cls
                created.append(name)

        existing_codes = {
            s.code for s in (await session.execute(select(Subject))).scalars().all()
        }
        subjects_by_code: dict[str, Subject] = {
            s.code: s for s in (await session.execute(select(Subject))).scalars().all()
        }
        for name, code in SUBJECTS:
            if code not in existing_codes:
                subject = Subject(name=name, code=code)
                session.add(subject)
                await session.flush()
                subjects_by_code[code] = subject
                created.append(f"subject {name}")

        admin = (
            await session.execute(select(User).where(User.login_id == "admin"))
        ).scalars().first()

        from app.services.security import hash_password

        if admin is None:
            admin = User(
                login_id="admin",
                password_hash=hash_password(ADMIN_PASSWORD),
                email="admin@knowledgeacademy.edu.in",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
            )
            session.add(admin)
            created.append("super_admin user 'admin'")
            await session.flush()

            # ── Layer 2: demo walkthrough data (first run only) ─────────
            await _seed_demo_walkthrough(session, existing_classes, subjects_by_code, year)
            created.append("demo walkthrough dataset (see DEMO_CREDENTIALS.md)")

        await session.commit()
        if created:
            print(f"seed_prod: created {len(created)} items: {', '.join(created[:10])}"
                  + ("…" if len(created) > 10 else ""))
        else:
            print("seed_prod: nothing to do (already seeded)")

        if "demo walkthrough dataset (see DEMO_CREDENTIALS.md)" in created:
            _print_credentials()


async def _seed_demo_walkthrough(
    session, classes: dict[str, Class], subjects: dict[str, Subject], year: AcademicYear
) -> None:
    """Populates enough realistic data to click through every portal page."""
    class3 = classes["Class 3"]
    class4 = classes["Class 4"]

    # Class 3 gets a second section; Class 4 keeps its bootstrap section "A".
    sec3a = (
        await session.execute(
            select(Section).where(Section.class_id == class3.id, Section.name == "A")
        )
    ).scalars().first()
    sec3b = Section(name="B", class_id=class3.id)
    session.add(sec3b)
    sec4a = (
        await session.execute(
            select(Section).where(Section.class_id == class4.id, Section.name == "A")
        )
    ).scalars().first()
    await session.flush()

    eng, hin, math, sci, sst = (
        subjects["ENG101"], subjects["HIN101"], subjects["MAT101"],
        subjects["SCI101"], subjects["SST101"],
    )

    # ── Teachers ─────────────────────────────────────────────────────────
    t1 = Staff(first_name="Sunita", last_name="Kaul", phone="9876543211",
               email="sunita@knowledgeacademy.edu.in", qualification="M.Sc. (Maths), B.Ed.",
               designation="PRT Mathematics")
    t2 = Staff(first_name="Ramesh", last_name="Joshi", phone="9876543212",
               email="ramesh@knowledgeacademy.edu.in", qualification="M.Sc. (Science), B.Ed.",
               designation="TGT Science")
    t3 = Staff(first_name="Priya", last_name="Sen", phone="9876543213",
               email="priya@knowledgeacademy.edu.in", qualification="M.A. (English), B.Ed.",
               designation="PRT English")
    session.add_all([t1, t2, t3])
    await session.flush()

    sec3a.class_teacher_id = t1.id
    sec3b.class_teacher_id = t3.id
    sec4a.class_teacher_id = t2.id

    session.add_all([
        StaffSubjectAssignment(staff_id=t1.id, subject_id=math.id, class_id=class3.id, section_id=sec3a.id),
        StaffSubjectAssignment(staff_id=t1.id, subject_id=math.id, class_id=class3.id, section_id=sec3b.id),
        StaffSubjectAssignment(staff_id=t1.id, subject_id=math.id, class_id=class4.id, section_id=sec4a.id),
        StaffSubjectAssignment(staff_id=t2.id, subject_id=sci.id, class_id=class3.id, section_id=sec3a.id),
        StaffSubjectAssignment(staff_id=t2.id, subject_id=sst.id, class_id=class4.id, section_id=sec4a.id),
        StaffSubjectAssignment(staff_id=t3.id, subject_id=eng.id, class_id=class3.id, section_id=sec3a.id),
        StaffSubjectAssignment(staff_id=t3.id, subject_id=eng.id, class_id=class3.id, section_id=sec3b.id),
        StaffSubjectAssignment(staff_id=t3.id, subject_id=hin.id, class_id=class4.id, section_id=sec4a.id),
    ])

    # ── Students (4 in 3-A, 3 in 3-B, 3 in 4-A) ─────────────────────────
    student_specs = [
        ("Aarav", "Sharma", "male", sec3a, 1, "Rakesh Sharma", "9876543220"),
        ("Riya", "Verma", "female", sec3a, 2, "Suman Verma", "9876543221"),
        ("Ishaan", "Gupta", "male", sec3a, 3, "Anil Gupta", "9876543222"),
        ("Ananya", "Iyer", "female", sec3a, 4, "Lakshmi Iyer", "9876543223"),
        ("Kabir", "Khan", "male", sec3b, 1, "Imran Khan", "9876543224"),
        ("Diya", "Patel", "female", sec3b, 2, "Nikhil Patel", "9876543225"),
        ("Vivaan", "Reddy", "male", sec3b, 3, "Sujatha Reddy", "9876543226"),
        ("Myra", "Nair", "female", sec4a, 1, "Ajay Nair", "9876543227"),
        ("Arjun", "Menon", "male", sec4a, 2, "Deepa Menon", "9876543228"),
        ("Saanvi", "Rao", "female", sec4a, 3, "Kiran Rao", "9876543229"),
    ]
    students: list[Student] = []
    for idx, (first, last, gender, section, roll, parent_name, parent_phone) in enumerate(
        student_specs, start=1
    ):
        student = Student(
            admission_number=f"ADM-{idx:05d}",
            first_name=first,
            last_name=last,
            dob=date(2019 - (idx % 2), 4 + idx % 8, 5 + idx),
            gender=gender,
            class_id=section.class_id,
            section_id=section.id,
            roll_number=roll,
            address=f"House {idx}, Green Avenue, New Delhi",
            documents={},
        )
        session.add(student)
        await session.flush()
        session.add(Parent(
            name=parent_name, phone=parent_phone, relation="father" if idx % 2 else "mother",
            whatsapp_number=parent_phone, student_id=student.id,
        ))
        students.append(student)

    # ── Logins ───────────────────────────────────────────────────────────
    from app.services.security import hash_password

    session.add_all([
        User(login_id="EMP-001", password_hash=hash_password(TEACHER_PASSWORD),
             email=t1.email, phone=t1.phone, role=UserRole.TEACHER,
             linked_staff_id=t1.id, is_active=True),
        User(login_id="EMP-002", password_hash=hash_password(TEACHER_PASSWORD),
             email=t2.email, phone=t2.phone, role=UserRole.TEACHER,
             linked_staff_id=t2.id, is_active=True),
        User(login_id="EMP-003", password_hash=hash_password(TEACHER_PASSWORD),
             email=t3.email, phone=t3.phone, role=UserRole.TEACHER,
             linked_staff_id=t3.id, is_active=True),
    ])
    for idx, student in enumerate(students, start=1):
        session.add(User(
            login_id=student.admission_number,
            password_hash=hash_password(STUDENT_PASSWORD),
            role=UserRole.STUDENT,
            linked_student_id=student.id,
            is_active=True,
        ))
    await session.flush()

    # ── Attendance: last 10 school days, realistic mix ──────────────────
    # students[2] (Ishaan) is chronically absent — good for absence-alert demos.
    school_days = _recent_weekdays(10, before=date.today())
    for day_idx, day in enumerate(school_days):
        for s_idx, student in enumerate(students):
            if s_idx == 2:
                status = AttendanceStatus.ABSENT if day_idx % 4 != 0 else AttendanceStatus.PRESENT
            elif s_idx == 5:
                status = AttendanceStatus.LATE if day_idx % 3 == 0 else AttendanceStatus.PRESENT
            elif (s_idx + day_idx) % 7 == 0:
                status = AttendanceStatus.ABSENT
            else:
                status = AttendanceStatus.PRESENT
            session.add(Attendance(student_id=student.id, date=day, status=status, marked_by_id=None))

    # ── Homework: 2 subjects, mixed submission states ───────────────────
    hw_math = Homework(
        class_id=class3.id, section_id=sec3a.id, subject_id=math.id, assigned_by_id=t1.id,
        title="Fractions worksheet", description="Complete exercises 1-10 on equivalent fractions.",
        due_date=datetime.combine(date.today() + timedelta(days=3), datetime.min.time()),
    )
    hw_eng = Homework(
        class_id=class3.id, section_id=sec3a.id, subject_id=eng.id, assigned_by_id=t3.id,
        title="Short story writing", description="Write a 150-word story about your favourite festival.",
        due_date=datetime.combine(date.today() + timedelta(days=5), datetime.min.time()),
    )
    session.add_all([hw_math, hw_eng])
    await session.flush()

    sec3a_students = [s for s in students if s.section_id == sec3a.id]
    # Math: student0 reviewed, student1 submitted (pending review), student2/3 not submitted.
    session.add(HomeworkSubmission(
        homework_id=hw_math.id, student_id=sec3a_students[0].id,
        submission_url="https://example.com/submissions/aarav-math.jpg",
        submitted_at=datetime.now() - timedelta(days=1),
        status=SubmissionStatus.REVIEWED, remarks="Good work, watch question 7.",
    ))
    session.add(HomeworkSubmission(
        homework_id=hw_math.id, student_id=sec3a_students[1].id,
        submission_url="https://example.com/submissions/riya-math.jpg",
        submitted_at=datetime.now() - timedelta(hours=6),
        status=SubmissionStatus.SUBMITTED,
    ))
    # English: only student0 has submitted so far.
    session.add(HomeworkSubmission(
        homework_id=hw_eng.id, student_id=sec3a_students[0].id,
        submission_url="https://example.com/submissions/aarav-story.jpg",
        submitted_at=datetime.now() - timedelta(hours=12),
        status=SubmissionStatus.SUBMITTED,
    ))

    # ── Exams: one published, one locked-but-unpublished (proves FR-16) ─
    exam_published = Exam(
        name="Half-Yearly Exam", academic_year_id=year.id, class_id=class3.id,
        exam_type="Half-Yearly", start_date=date.today() - timedelta(days=20),
        end_date=date.today() - timedelta(days=15), is_locked=True, results_published=True,
    )
    session.add(exam_published)
    await session.flush()
    es_math = ExamSubject(exam_id=exam_published.id, subject_id=math.id, max_marks=100, passing_marks=33)
    es_eng = ExamSubject(exam_id=exam_published.id, subject_id=eng.id, max_marks=100, passing_marks=33)
    session.add_all([es_math, es_eng])
    await session.flush()

    class3_students = [s for s in students if s.class_id == class3.id]
    marks_math = [88, 72, 45, 91, 60, 78, 55]
    marks_eng = [76, 82, 39, 95, 70, 60, 48]
    for student, m_math, m_eng in zip(class3_students, marks_math, marks_eng):
        session.add(Mark(exam_subject_id=es_math.id, student_id=student.id,
                          marks_obtained=m_math, is_submitted=True))
        session.add(Mark(exam_subject_id=es_eng.id, student_id=student.id,
                          marks_obtained=m_eng, is_submitted=True))

    exam_unpublished = Exam(
        name="Unit Test 2", academic_year_id=year.id, class_id=class3.id,
        exam_type="Unit Test", start_date=date.today() - timedelta(days=3),
        end_date=date.today() - timedelta(days=1), is_locked=True, results_published=False,
    )
    session.add(exam_unpublished)
    await session.flush()
    es_ut_math = ExamSubject(exam_id=exam_unpublished.id, subject_id=math.id, max_marks=50, passing_marks=17)
    session.add(es_ut_math)
    await session.flush()
    for student, m in zip(class3_students, [40, 35, 20, 47, 30, 38, 25]):
        session.add(Mark(exam_subject_id=es_ut_math.id, student_id=student.id,
                          marks_obtained=m, is_submitted=True))

    # Still open, no marks entered — populates the "Pending Marks Entry"
    # card on t1's (EMP-001) teacher dashboard.
    exam_open = Exam(
        name="Unit Test 1", academic_year_id=year.id, class_id=class4.id,
        exam_type="Unit Test", start_date=date.today() + timedelta(days=2),
        end_date=date.today() + timedelta(days=3), is_locked=False, results_published=False,
    )
    session.add(exam_open)
    await session.flush()
    session.add(ExamSubject(exam_id=exam_open.id, subject_id=math.id, max_marks=50, passing_marks=17))

    # ── Fees: Tuition (all Class 3) — full/partial/defaulter mix ────────
    tuition = FeeStructure(class_id=class3.id, academic_year_id=year.id, fee_head="Tuition Fee",
                           amount=8000, due_date=date.today() - timedelta(days=20), term="Term 1")
    exam_fee = FeeStructure(class_id=class3.id, academic_year_id=year.id, fee_head="Exam Fee",
                             amount=1200, due_date=date.today() - timedelta(days=10), term="Term 1")
    session.add_all([tuition, exam_fee])
    await session.flush()

    def _receipt(n: int) -> str:
        return f"RCT-{n:05d}"

    def _months_ago(n: int) -> datetime:
        """Approximate 'n months ago' — spreads demo payments across the
        6-month collection chart instead of dumping everything in today's
        bucket. Balances are unaffected (they sum by student, not by date)."""
        year, month = date.today().year, date.today().month - n
        while month <= 0:
            month += 12
            year -= 1
        return datetime(year, month, min(date.today().day, 28), 11, 0)

    receipt_no = 1
    for idx, student in enumerate(class3_students):
        if idx == 0:  # fully paid both heads, a few months back
            session.add(FeeTransaction(student_id=student.id, fee_structure_id=tuition.id,
                                        amount_paid=8000, payment_mode=PaymentMode.ONLINE,
                                        paid_at=_months_ago(4),
                                        receipt_number=_receipt(receipt_no))); receipt_no += 1
            session.add(FeeTransaction(student_id=student.id, fee_structure_id=exam_fee.id,
                                        amount_paid=1200, payment_mode=PaymentMode.CASH,
                                        paid_at=_months_ago(3),
                                        receipt_number=_receipt(receipt_no))); receipt_no += 1
        elif idx == 1:  # partially paid tuition, unpaid exam fee
            session.add(FeeTransaction(student_id=student.id, fee_structure_id=tuition.id,
                                        amount_paid=4000, payment_mode=PaymentMode.CASH,
                                        paid_at=_months_ago(2),
                                        receipt_number=_receipt(receipt_no))); receipt_no += 1
        elif idx == 2:  # zero paid — clearest defaulter
            pass
        else:  # rest: fully paid tuition only, spread across last month + this month
            months_back = 1 if idx % 2 == 0 else 0
            session.add(FeeTransaction(student_id=student.id, fee_structure_id=tuition.id,
                                        amount_paid=8000, payment_mode=PaymentMode.CASH,
                                        paid_at=_months_ago(months_back),
                                        receipt_number=_receipt(receipt_no))); receipt_no += 1

    # ── Notices: everyone / class-targeted / staff-only ─────────────────
    now = datetime.now()
    session.add_all([
        Notice(title="School Reopening after Summer Vacation",
               content="Classes resume Monday, July 1st. Please collect syllabus folders from the office.",
               audience=NoticeAudience.EVERYONE, channels=["website", "app"],
               published_at=now - timedelta(days=15), created_by_id=None),
        Notice(title="Class 3 Half-Yearly Datesheet",
               content="Half-Yearly exams for Class 3 begin next week. Datesheet has been shared with class teachers.",
               audience=NoticeAudience.CLASS, target_class_id=class3.id, channels=["app", "whatsapp"],
               published_at=now - timedelta(days=21), created_by_id=None),
        Notice(title="Staff Meeting — Friday 4 PM",
               content="All teaching staff to attend the monthly review meeting in the staff room.",
               audience=NoticeAudience.STAFF, channels=["app"],
               published_at=now - timedelta(days=2), created_by_id=None),
        Notice(title="Sports Day Practice Schedule",
               content="Class 3 sports day practice will be held every morning this week before assembly.",
               audience=NoticeAudience.CLASS, target_class_id=class3.id, channels=["app"],
               published_at=now - timedelta(hours=6), created_by_id=None),
    ])

    # ── Timetable: full week for Class 3 - A ────────────────────────────
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    period_plan = [
        (math.id, t1.id), (eng.id, t3.id), (sci.id, t2.id),
        (math.id, t1.id), (eng.id, t3.id), (sci.id, t2.id),
    ]
    for day in days:
        for period_number, (subject_id, staff_id) in enumerate(period_plan, start=1):
            session.add(TimetableSlot(
                class_id=class3.id, section_id=sec3a.id, day_of_week=day,
                period_number=period_number, subject_id=subject_id, staff_id=staff_id,
            ))

    # ── Admission enquiries: staged pipeline ────────────────────────────
    session.add_all([
        AdmissionEnquiry(child_name="Advait Malhotra", dob=date(2021, 3, 12), class_applying="Nursery",
                         parent_name="Rohit Malhotra", phone="9123456780", email="rohit.m@example.com",
                         source="website", status=EnquiryStatus.NEW,
                         message="Looking for a nursery admission for the new session."),
        AdmissionEnquiry(child_name="Ira Bhatt", dob=date(2018, 7, 22), class_applying="Class 2",
                         parent_name="Neha Bhatt", phone="9123456781", email="neha.b@example.com",
                         source="referral", status=EnquiryStatus.CONTACTED,
                         notes="Called on Monday, scheduling a campus visit next week."),
        AdmissionEnquiry(child_name="Yuvan Chawla", dob=date(2016, 11, 3), class_applying="Class 4",
                         parent_name="Sameer Chawla", phone="9123456782", email="sameer.c@example.com",
                         source="walk-in", status=EnquiryStatus.ADMITTED,
                         notes="Visited campus, documents verified, admitted."),
    ])

    # ── Contact messages ─────────────────────────────────────────────────
    session.add_all([
        ContactMessage(name="Pooja Sharma", email="pooja.s@example.com", phone="9988776655",
                       message="What are the school timings for the primary section?", is_read=False),
        ContactMessage(name="Manoj Kumar", email="manoj.k@example.com", phone="9988776656",
                       message="Do you offer transport for Sector 9?", is_read=True),
    ])


def _print_credentials() -> None:
    print("\n" + "=" * 60)
    print("DEMO LOGIN CREDENTIALS (also see DEMO_CREDENTIALS.md)")
    print("=" * 60)
    print(f"  Super Admin : admin          / {ADMIN_PASSWORD}")
    print(f"  Teachers    : EMP-001/002/003 / {TEACHER_PASSWORD}")
    print(f"  Students    : ADM-00001..00010 / {STUDENT_PASSWORD}")
    print("  (parents sign in with their child's student login)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_production())

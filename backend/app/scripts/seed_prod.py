"""Idempotent demo seed.

Two independently-gated layers:
1. Bootstrap (`seed_production`, always runs, per-item idempotent, cheap —
   wired to SEED_ON_START and safe on every Render boot): school profile,
   current academic year, 15 classes x 2 sections each, subject catalog,
   fee structures, a super_admin login.
2. Full demo dataset (`seed_demo_dataset`, gated on "does any Student exist
   yet" — NOT on the admin login, so wiping Users alone can't re-trigger
   it): ~25-30 teachers, 300 students, attendance, exams/marks, fees,
   homework, notices, a full timetable, admissions, contact messages.
   This is NOT called from app startup — it's heavy (~18k rows) and is
   meant to be run once, manually, via `python -m app.scripts.seed_prod`
   pointed at the target database. See DEMO_CREDENTIALS.md.

Credentials: representative sample in DEMO_CREDENTIALS.md (repo root),
full 300-student list in STUDENT_CREDENTIALS.csv (repo root) — both
written by this script when the demo dataset runs.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date, datetime, timedelta, timezone
from itertools import count
from pathlib import Path

from sqlalchemy import insert, select

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
from app.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
RNG_SEED = 20260709
CHUNK_SIZE = 1000

CLASS_NAMES = ["Nursery", "LKG", "UKG"] + [f"Class {n}" for n in range(1, 13)]
SECTION_NAMES = ["A", "B"]
STUDENTS_PER_SECTION = 10
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

# Bootstrap admin password comes from settings (ADMIN_BOOTSTRAP_PASSWORD env
# var in production — see config.py) so a real deployment's admin password
# is never a literal committed to source control. Demo teacher/student
# passwords stay as documented constants: they belong to the full demo
# dataset, which only ever runs manually/locally, never on a live boot.
ADMIN_PASSWORD = settings.admin_bootstrap_password
TEACHER_PASSWORD = "Teach@2026"
STUDENT_PASSWORD = "Study@2026"

# Subject is a completely flat/global table in this schema (no class_id, no
# level tag) — see plan notes. This tiering exists ONLY in the seed script;
# the platform itself would let an admin assign any subject to any class.
SUBJECTS = [
    ("Rhymes & Stories", "RHY101"), ("Art & Craft", "ART101"),
    ("Basic Numeracy", "NUM101"), ("Basic Literacy", "LIT101"),
    ("Physical Education", "PED101"), ("English", "ENG101"),
    ("Hindi", "HIN101"), ("Mathematics", "MAT101"),
    ("Environmental Studies", "EVS101"), ("Computer Science", "CSC101"),
    ("Science", "SCI101"), ("Social Science", "SST101"),
    ("General Knowledge", "GKN101"), ("Physics", "PHY101"),
    ("Chemistry", "CHM101"), ("Biology", "BIO101"),
    ("Economics", "ECO101"), ("Business Studies", "BST101"),
    ("Accountancy", "ACC101"),
]

# tier -> (subject codes, periods/day). Period density rises with grade
# level (realistic — junior classes have shorter days) which is also what
# keeps total weekly demand achievable with a realistic teacher headcount;
# see the completion report for the scheduling-math reasoning.
TIER_SUBJECTS = {
    1: (["RHY101", "ART101", "NUM101", "LIT101", "PED101"], 3),
    2: (["ENG101", "HIN101", "MAT101", "EVS101", "CSC101", "ART101", "PED101"], 4),
    3: (["ENG101", "HIN101", "MAT101", "SCI101", "SST101", "CSC101", "GKN101", "PED101"], 4),
    4: (["ENG101", "MAT101", "PHY101", "CHM101", "BIO101", "ECO101", "BST101", "ACC101", "CSC101"], 5),
}
TEACHER_WEEKLY_CAP = 28

FEMALE_FIRST = ["Ananya", "Diya", "Saanvi", "Aadhya", "Myra", "Aarohi", "Ira", "Kiara",
    "Anika", "Riya", "Navya", "Pari", "Sara", "Zara", "Avni", "Ishita", "Tara", "Prisha",
    "Meera", "Aditi", "Kavya", "Nisha", "Pooja", "Shreya", "Sneha", "Trisha", "Vanya",
    "Yashvi", "Anvi", "Bhavya", "Charvi", "Disha", "Esha", "Falak", "Gauri", "Hiya",
    "Ishani", "Jiya", "Khushi", "Lavanya"]
MALE_FIRST = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Rohan", "Kabir", "Aryan", "Dhruv", "Karthik", "Aniket", "Rudra",
    "Yash", "Om", "Devansh", "Harsh", "Nikhil", "Siddharth", "Varun", "Manav", "Pranav",
    "Rishi", "Tanish", "Veer", "Yuvraj", "Aarush", "Atharv", "Advait", "Kian", "Shaurya",
    "Vedant", "Parth", "Naman", "Arnav", "Kartik"]
SURNAMES = ["Sharma", "Verma", "Gupta", "Iyer", "Khan", "Patel", "Reddy", "Nair", "Menon",
    "Rao", "Kapoor", "Malhotra", "Bhatt", "Chawla", "Joshi", "Kaul", "Sen", "Singh",
    "Kumar", "Das", "Chatterjee", "Mukherjee", "Banerjee", "Bose", "Pillai", "Naidu",
    "Chauhan", "Yadav", "Mishra", "Tiwari", "Agarwal", "Bansal", "Chopra", "Dutta",
    "Ghosh", "Hegde", "Jain", "Kulkarni", "Mehta", "Pandey"]
AREAS = ["Sector 5", "Sector 12", "Green Park", "Model Town", "Civil Lines",
    "Rajouri Garden", "Lajpat Nagar", "Vasant Kunj", "Dwarka Sector 21",
    "Rohini Sector 8", "Pitampura", "Shalimar Bagh", "Mayur Vihar", "Preet Vihar",
    "Janakpuri"]


def _tier(numeric_order: int) -> int:
    if numeric_order <= 3:
        return 1
    if numeric_order <= 7:
        return 2
    if numeric_order <= 11:
        return 3
    return 4


def _weekdays_last_n_days(days_back: int, before: date) -> list[date]:
    """Every Mon-Sat date in the last `days_back` calendar days before `before`."""
    out = []
    for offset in range(days_back, 0, -1):
        d = before - timedelta(days=offset)
        if d.weekday() != 6:
            out.append(d)
    return out


def _receipt(n: int) -> str:
    return f"RCT-{n:06d}"


def _months_ago(n: int) -> datetime:
    """Approximate 'n months ago', tz-aware (matches paid_at's tz-aware column)."""
    year, month = date.today().year, date.today().month - n
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, min(date.today().day, 28), 11, 0, tzinfo=timezone.utc)


def _phone(rng: random.Random) -> str:
    return str(rng.choice([6, 7, 8, 9])) + "".join(str(rng.randint(0, 9)) for _ in range(9))


def _address(rng: random.Random) -> str:
    return f"House {rng.randint(1, 400)}, {rng.choice(AREAS)}, New Delhi - {110000 + rng.randint(1, 95)}"


def _dob_for_level(numeric_order: int, rng: random.Random) -> date:
    base_age = numeric_order + 2  # Nursery(1)~3yo .. Class12(15)~17yo
    year = date(2026, 4, 1).year - base_age
    return date(year, rng.randint(1, 12), rng.randint(1, 28))


def _admission_created_at(rng: random.Random, recent: bool) -> datetime:
    now = datetime.now(timezone.utc)
    days_back = rng.randint(1, 55) if recent else rng.randint(120, 1460)
    return now - timedelta(days=days_back)


async def seed_production() -> None:
    """Bootstrap layer only — cheap, self-healing, safe on every boot."""
    async with async_session_factory() as session:
        created: list[str] = []

        school = (await session.execute(select(School))).scalars().first()
        if school is None:
            session.add(School(
                name="Knowledge Development Kindergarten Academy",
                address="Basopatti Road, Near Ugna Chawk, Benipatti, Madhubani, Bihar 847223",
                # No CBSE affiliation number yet — the school's own current
                # marketing says affiliation is pending ("to be affiliated"),
                # not granted. Leave blank rather than seed a fake number.
                affiliation_number=None,
                contact_email="info@knowledgeacademy.edu.in",
                contact_phone="+91 99349 75151 / +91 99731 04141",
                settings={"allow_online_fees": True, "automation": {}},
            ))
            created.append("school")

        year = (await session.execute(
            select(AcademicYear).where(AcademicYear.is_current)
        )).scalars().first()
        if year is None:
            year = AcademicYear(label="2026-27", start_date=date(2026, 4, 1),
                                 end_date=date(2027, 3, 31), is_current=True)
            session.add(year)
            await session.flush()
            created.append("academic year 2026-27")

        existing_classes = {c.name: c for c in (await session.execute(select(Class))).scalars().all()}
        for order, name in enumerate(CLASS_NAMES, start=1):
            if name not in existing_classes:
                cls = Class(name=name, numeric_order=order)
                session.add(cls)
                await session.flush()
                existing_classes[name] = cls
                created.append(name)

        existing_sections = {
            (s.class_id, s.name) for s in (await session.execute(select(Section))).scalars().all()
        }
        for name, cls in existing_classes.items():
            for sec_name in SECTION_NAMES:
                if (cls.id, sec_name) not in existing_sections:
                    session.add(Section(name=sec_name, class_id=cls.id))
                    created.append(f"section {name}-{sec_name}")
        await session.flush()

        existing_codes = {s.code for s in (await session.execute(select(Subject))).scalars().all()}
        for name, code in SUBJECTS:
            if code not in existing_codes:
                session.add(Subject(name=name, code=code))
                created.append(f"subject {name}")
        await session.flush()

        existing_fee_keys = {
            (f.class_id, f.fee_head) for f in (await session.execute(select(FeeStructure))).scalars().all()
        }
        for name, cls in existing_classes.items():
            order = cls.numeric_order
            tuition = 6000 + order * 400
            exam_fee = 800 + order * 100
            if (cls.id, "Tuition Fee") not in existing_fee_keys:
                session.add(FeeStructure(class_id=cls.id, academic_year_id=year.id,
                    fee_head="Tuition Fee", amount=tuition,
                    due_date=date.today() - timedelta(days=20), term="Term 1"))
                created.append(f"fee structure {name} Tuition")
            if (cls.id, "Exam Fee") not in existing_fee_keys:
                session.add(FeeStructure(class_id=cls.id, academic_year_id=year.id,
                    fee_head="Exam Fee", amount=exam_fee,
                    due_date=date.today() - timedelta(days=10), term="Term 1"))
                created.append(f"fee structure {name} Exam Fee")

        from app.services.security import hash_password

        admin = (await session.execute(select(User).where(User.login_id == "admin"))).scalars().first()
        if admin is None:
            session.add(User(login_id="admin", password_hash=hash_password(ADMIN_PASSWORD),
                email="admin@knowledgeacademy.edu.in", role=UserRole.SUPER_ADMIN, is_active=True))
            created.append("super_admin user 'admin'")

        await session.commit()
        if created:
            print(f"seed_prod (bootstrap): created {len(created)} items: "
                  + ", ".join(created[:10]) + ("…" if len(created) > 10 else ""))
        else:
            print("seed_prod (bootstrap): nothing to do (already seeded)")


async def seed_demo_dataset() -> None:
    """Heavy per-person walkthrough dataset. NOT called on boot — run this
    manually: `python -m app.scripts.seed_prod` (runs bootstrap + this)."""
    async with async_session_factory() as session:
        already = (await session.execute(select(Student.id).limit(1))).scalar_one_or_none()
        if already is not None:
            print("seed_prod (demo dataset): already seeded, skipping")
            return

        rng = random.Random(RNG_SEED)

        classes = {c.name: c for c in (await session.execute(select(Class))).scalars().all()}
        sections_by_class: dict[int, dict[str, Section]] = {}
        for sec in (await session.execute(select(Section))).scalars().all():
            sections_by_class.setdefault(sec.class_id, {})[sec.name] = sec
        subjects_by_code = {s.code: s for s in (await session.execute(select(Subject))).scalars().all()}
        year = (await session.execute(select(AcademicYear).where(AcademicYear.is_current))).scalars().first()

        # ── Teachers: pool size per tier computed from actual weekly demand,
        # not hand-picked, so it's always sufficient for the timetable pass
        # below. See completion report for why this lands above the initial
        # "20-25" estimate — a fully-populated 30-section timetable has a
        # hard mathematical floor on teacher count that a fixed target can't
        # dodge (a teacher can't be in two places in the same period).
        tier_pool_sizes: dict[int, int] = {}
        for tier, (codes, periods_per_day) in TIER_SUBJECTS.items():
            levels_in_tier = [c for c in classes.values() if _tier(c.numeric_order) == tier]
            weekly_demand = len(levels_in_tier) * 2 * periods_per_day * 6
            tier_pool_sizes[tier] = math.ceil(weekly_demand / TEACHER_WEEKLY_CAP)

        DESIGNATIONS = {1: "Pre-Primary Teacher", 2: "PRT", 3: "TGT", 4: "PGT"}
        regular: list[Staff] = []
        regular_specialty: dict[int, list[str]] = {}  # staff.id -> subject codes
        teacher_names_used: set[tuple[str, str]] = set()

        def _new_teacher_name() -> tuple[str, str]:
            while True:
                first = rng.choice(FEMALE_FIRST + MALE_FIRST)
                last = rng.choice(SURNAMES)
                if (first, last) not in teacher_names_used:
                    teacher_names_used.add((first, last))
                    return first, last

        for tier, (codes, _) in TIER_SUBJECTS.items():
            pool_size = tier_pool_sizes[tier]
            for i in range(pool_size):
                first, last = _new_teacher_name()
                staff = Staff(
                    first_name=first, last_name=last, phone=_phone(rng),
                    email=f"{first.lower()}.{last.lower()}{len(regular)+1}@knowledgeacademy.edu.in",
                    qualification="B.Ed." if tier <= 2 else "M.A./M.Sc., B.Ed.",
                    designation=DESIGNATIONS[tier],
                )
                session.add(staff)
                regular.append(staff)
                # 1-2 specialty subjects, round-robin through the tier's codes
                # so every subject in the tier has at least one teacher.
                specialty = [codes[i % len(codes)]]
                if len(codes) > pool_size:
                    specialty.append(codes[(i + pool_size) % len(codes)])
                regular_specialty[id(staff)] = specialty
        await session.flush()
        regular_specialty = {s.id: regular_specialty[id(s)] for s in regular}

        floating: list[Staff] = []
        for _ in range(4):
            first, last = _new_teacher_name()
            staff = Staff(
                first_name=first, last_name=last, phone=_phone(rng),
                email=f"{first.lower()}.{last.lower()}.float@knowledgeacademy.edu.in",
                qualification="B.Ed.", designation="Floating / Substitute Teacher",
            )
            session.add(staff)
            floating.append(staff)
        await session.flush()

        print(f"seed_prod (demo dataset): {len(regular)} regular + {len(floating)} floating teachers "
              f"({sum(tier_pool_sizes.values())} regular across 4 tiers, cap {TEACHER_WEEKLY_CAP}/week)")

        # ── Role assignment: greedy load-balanced bin-packing of every
        # (level, subject) role onto the lowest-loaded eligible teacher.
        role_teacher: dict[tuple[str, str], Staff] = {}
        staff_load: dict[int, float] = {s.id: 0.0 for s in regular}
        roles: list[tuple[str, str, float, int]] = []  # (level, code, weekly_periods, tier)
        for cname, cls in classes.items():
            tier = _tier(cls.numeric_order)
            codes, periods_per_day = TIER_SUBJECTS[tier]
            weekly_per_subject = (periods_per_day * 6 / len(codes)) * 2  # x2 sections
            for code in codes:
                roles.append((cname, code, weekly_per_subject, tier))
        roles.sort(key=lambda r: -r[2])  # largest first (LPT heuristic)

        for level_name, code, load, tier in roles:
            candidates = [s for s in regular if code in regular_specialty[s.id]]
            if not candidates:
                candidates = regular
            eligible = [s for s in candidates if staff_load[s.id] + load <= TEACHER_WEEKLY_CAP + 4]
            pool = eligible or candidates
            chosen = min(pool, key=lambda s: staff_load[s.id])
            role_teacher[(level_name, code)] = chosen
            staff_load[chosen.id] += load

        # class-teacher assignment: round-robin across regular teachers
        section_list: list[Section] = []
        for cname, cls in classes.items():
            for sec_name in SECTION_NAMES:
                section_list.append(sections_by_class[cls.id][sec_name])
        for i, sec in enumerate(section_list):
            sec.class_teacher_id = regular[i % len(regular)].id

        # StaffSubjectAssignment: one row per (level, subject, section)
        assignments = []
        for cname, cls in classes.items():
            tier = _tier(cls.numeric_order)
            codes, _ = TIER_SUBJECTS[tier]
            for code in codes:
                teacher = role_teacher[(cname, code)]
                subject = subjects_by_code[code]
                for sec_name in SECTION_NAMES:
                    sec = sections_by_class[cls.id][sec_name]
                    assignments.append(StaffSubjectAssignment(
                        staff_id=teacher.id, subject_id=subject.id,
                        class_id=cls.id, section_id=sec.id,
                    ))
        session.add_all(assignments)
        await session.flush()
        print(f"seed_prod (demo dataset): {len(assignments)} subject assignments, "
              f"{len(section_list)} class-teacher wirings")

        # ── Students: ONE flat list built up front (15 levels x 2 sections x
        # 10 students = 300), then a single pass creates all Student rows and
        # a single pass creates all matching User rows from that SAME list —
        # deliberately not nested per-section loops, so no level/section can
        # silently drop out partway through.
        student_specs: list[dict] = []
        admission_counter = count(1)
        for cname, cls in classes.items():
            for sec_name in SECTION_NAMES:
                sec = sections_by_class[cls.id][sec_name]
                for roll in range(1, STUDENTS_PER_SECTION + 1):
                    gender = "female" if roll % 2 == 0 else "male"
                    first = rng.choice(FEMALE_FIRST if gender == "female" else MALE_FIRST)
                    last = rng.choice(SURNAMES)
                    idx = next(admission_counter)
                    if roll == 1:
                        attendance_profile, fee_profile = "strong", "full"
                    elif roll == 2:
                        attendance_profile, fee_profile = "chronic", "defaulter"
                    else:
                        attendance_profile = "average"
                        fee_profile = rng.choices(
                            ["full", "partial", "unpaid"], weights=[40, 35, 25]
                        )[0]
                    recent = idx % 23 == 0
                    parent_first = rng.choice(FEMALE_FIRST + MALE_FIRST)
                    parent_last = last
                    student_specs.append(dict(
                        idx=idx, class_id=cls.id, section_id=sec.id, class_name=cname,
                        section_name=sec_name, roll=roll, first=first, last=last,
                        gender=gender, dob=_dob_for_level(cls.numeric_order, rng),
                        address=_address(rng), parent_name=f"{parent_first} {parent_last}",
                        parent_phone=_phone(rng), created_at=_admission_created_at(rng, recent),
                        attendance_profile=attendance_profile, fee_profile=fee_profile,
                    ))
        assert len(student_specs) == 300, f"expected 300 student specs, got {len(student_specs)}"

        students: list[Student] = []
        for spec in student_specs:
            student = Student(
                admission_number=f"ADM-{spec['idx']:05d}", first_name=spec["first"],
                last_name=spec["last"], dob=spec["dob"], gender=spec["gender"],
                class_id=spec["class_id"], section_id=spec["section_id"], roll_number=spec["roll"],
                address=spec["address"], documents={}, created_at=spec["created_at"],
            )
            session.add(student)
            students.append(student)
        await session.flush()
        for student, spec in zip(students, student_specs):
            spec["student_id"] = student.id
            session.add(Parent(
                name=spec["parent_name"], phone=spec["parent_phone"],
                relation="father" if spec["roll"] % 2 else "mother",
                whatsapp_number=spec["parent_phone"], student_id=student.id,
            ))

        from app.services.security import hash_password

        teacher_password_hash = hash_password(TEACHER_PASSWORD)
        student_password_hash = hash_password(STUDENT_PASSWORD)

        teacher_logins: list[dict] = []
        emp_counter = count(1)
        for staff in regular + floating:
            emp_id = f"EMP-{next(emp_counter):03d}"
            session.add(User(login_id=emp_id, password_hash=teacher_password_hash,
                email=staff.email, phone=staff.phone, role=UserRole.TEACHER,
                linked_staff_id=staff.id, is_active=True))
            teacher_logins.append(dict(
                login_id=emp_id, name=f"{staff.first_name} {staff.last_name}",
                designation=staff.designation,
                subjects=", ".join(sorted(set(regular_specialty.get(staff.id, ["—"])))),
                floating=staff in floating,
            ))
        for student, spec in zip(students, student_specs):
            session.add(User(login_id=student.admission_number, password_hash=student_password_hash,
                role=UserRole.STUDENT, linked_student_id=student.id, is_active=True))
        await session.flush()
        print(f"seed_prod (demo dataset): {len(students)} students, {len(teacher_logins)} teacher logins")

        # ── Attendance: last 60 calendar days, weekdays only, per-student
        # profile. Bulk Core insert — this is the largest table (~15k rows).
        school_days = _weekdays_last_n_days(60, before=date.today())
        attendance_rows: list[dict] = []
        for student, spec in zip(students, student_specs):
            profile = spec["attendance_profile"]
            if profile == "chronic":
                present_rate = rng.uniform(0.40, 0.58)
            elif profile == "strong":
                present_rate = rng.uniform(0.92, 0.97)
            else:
                present_rate = rng.uniform(0.75, 0.95)
            for day in school_days:
                roll = rng.random()
                if roll < present_rate:
                    status = AttendanceStatus.PRESENT
                elif roll < present_rate + 0.06:
                    status = AttendanceStatus.LATE
                else:
                    status = AttendanceStatus.ABSENT
                attendance_rows.append(dict(
                    student_id=student.id, date=day, status=status, marked_by_id=None,
                ))
        for i in range(0, len(attendance_rows), CHUNK_SIZE):
            await session.execute(insert(Attendance), attendance_rows[i:i + CHUNK_SIZE])
        print(f"seed_prod (demo dataset): {len(attendance_rows)} attendance rows "
              f"across {len(school_days)} school days")

        # ── Exams/Marks: Class 1-12 only, 3 exams/level (published+full,
        # locked-unpublished+full [proves FR-16], unlocked+zero-marks
        # [feeds the teacher pending-marks queue]).
        students_by_class: dict[int, list[Student]] = {}
        for student, spec in zip(students, student_specs):
            students_by_class.setdefault(spec["class_id"], []).append(student)

        mark_rows: list[dict] = []
        exam_count = 0
        for cname, cls in classes.items():
            if cls.numeric_order <= 3:  # Nursery/LKG/UKG — no formal exams
                continue
            tier = _tier(cls.numeric_order)
            codes, _ = TIER_SUBJECTS[tier]
            exam_subject_codes = codes[:2]
            class_students = students_by_class[cls.id]

            exam_pub = Exam(name="Unit Test 1", academic_year_id=year.id, class_id=cls.id,
                exam_type="Unit Test", start_date=date.today() - timedelta(days=25),
                end_date=date.today() - timedelta(days=22), is_locked=True, results_published=True)
            session.add(exam_pub)
            await session.flush()
            for code in exam_subject_codes:
                es = ExamSubject(exam_id=exam_pub.id, subject_id=subjects_by_code[code].id,
                                  max_marks=100, passing_marks=33)
                session.add(es)
                await session.flush()
                for student in class_students:
                    mark_rows.append(dict(exam_subject_id=es.id, student_id=student.id,
                        marks_obtained=round(rng.uniform(28, 98), 1), grade=None,
                        entered_by_id=None, is_submitted=True))

            exam_unpub = Exam(name="Half-Yearly Exam", academic_year_id=year.id, class_id=cls.id,
                exam_type="Half-Yearly", start_date=date.today() - timedelta(days=10),
                end_date=date.today() - timedelta(days=7), is_locked=True, results_published=False)
            session.add(exam_unpub)
            await session.flush()
            for code in exam_subject_codes:
                es = ExamSubject(exam_id=exam_unpub.id, subject_id=subjects_by_code[code].id,
                                  max_marks=100, passing_marks=33)
                session.add(es)
                await session.flush()
                for student in class_students:
                    mark_rows.append(dict(exam_subject_id=es.id, student_id=student.id,
                        marks_obtained=round(rng.uniform(25, 96), 1), grade=None,
                        entered_by_id=None, is_submitted=True))

            exam_open = Exam(name="Unit Test 2", academic_year_id=year.id, class_id=cls.id,
                exam_type="Unit Test", start_date=date.today() + timedelta(days=3),
                end_date=date.today() + timedelta(days=4), is_locked=False, results_published=False)
            session.add(exam_open)
            await session.flush()
            session.add(ExamSubject(exam_id=exam_open.id, subject_id=subjects_by_code[exam_subject_codes[0]].id,
                                     max_marks=100, passing_marks=33))
            exam_count += 3

        for i in range(0, len(mark_rows), CHUNK_SIZE):
            await session.execute(insert(Mark), mark_rows[i:i + CHUNK_SIZE])
        await session.flush()
        print(f"seed_prod (demo dataset): {exam_count} exams, {len(mark_rows)} marks")

        # ── Fee transactions: per-student profile (full/partial/unpaid),
        # spread across months for the collection-trend chart.
        fee_structures = (await session.execute(select(FeeStructure))).scalars().all()
        fee_by_class: dict[int, list[FeeStructure]] = {}
        for fs in fee_structures:
            fee_by_class.setdefault(fs.class_id, []).append(fs)

        receipt_counter = count(1)
        fee_rows: list[dict] = []
        for student, spec in zip(students, student_specs):
            heads = fee_by_class.get(spec["class_id"], [])
            profile = spec["fee_profile"]
            for head_idx, fs in enumerate(heads):
                months_back = rng.choice([0, 1, 2, 3, 4, 5])
                mode = rng.choice([PaymentMode.CASH, PaymentMode.ONLINE, PaymentMode.CHEQUE])
                if profile == "full":
                    fee_rows.append(dict(student_id=student.id, fee_structure_id=fs.id,
                        amount_paid=fs.amount, payment_mode=mode, razorpay_payment_id=None,
                        receipt_number=_receipt(next(receipt_counter)),
                        paid_at=_months_ago(months_back), refund_reason=None))
                elif profile == "partial":
                    if head_idx == 0:  # partially pay just the first head
                        fee_rows.append(dict(student_id=student.id, fee_structure_id=fs.id,
                            amount_paid=round(fs.amount * rng.uniform(0.3, 0.7), 2), payment_mode=mode,
                            razorpay_payment_id=None, receipt_number=_receipt(next(receipt_counter)),
                            paid_at=_months_ago(months_back), refund_reason=None))
                    # else: unpaid on remaining heads
                # "unpaid": no transactions at all

        for i in range(0, len(fee_rows), CHUNK_SIZE):
            await session.execute(insert(FeeTransaction), fee_rows[i:i + CHUNK_SIZE])
        print(f"seed_prod (demo dataset): {len(fee_rows)} fee transactions")

        # ── Homework: 2 per section (varied subjects), mixed submission
        # states across the section's students.
        students_by_section: dict[int, list[Student]] = {}
        for student, spec in zip(students, student_specs):
            students_by_section.setdefault(spec["section_id"], []).append(student)

        homework_rows = 0
        submission_rows: list[dict] = []
        for cname, cls in classes.items():
            tier = _tier(cls.numeric_order)
            codes, _ = TIER_SUBJECTS[tier]
            for sec_name in SECTION_NAMES:
                sec = sections_by_class[cls.id][sec_name]
                sec_students = students_by_section[sec.id]
                for code in codes[:2]:
                    teacher = role_teacher[(cname, code)]
                    subject = subjects_by_code[code]
                    hw = Homework(class_id=cls.id, section_id=sec.id, subject_id=subject.id,
                        assigned_by_id=teacher.id, title=f"{subject.name} Assignment",
                        description=f"Complete the {subject.name} worksheet and submit online.",
                        due_date=datetime.combine(date.today() + timedelta(days=rng.randint(2, 7)), datetime.min.time()))
                    session.add(hw)
                    await session.flush()
                    homework_rows += 1
                    shuffled = sec_students[:]
                    rng.shuffle(shuffled)
                    for i, student in enumerate(shuffled):
                        if i < 4:
                            submission_rows.append(dict(homework_id=hw.id, student_id=student.id,
                                submission_url=f"https://example.com/submissions/{student.admission_number}-{code}.jpg",
                                submitted_at=datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 4)),
                                status=SubmissionStatus.REVIEWED, remarks="Good work."))
                        elif i < 7:
                            submission_rows.append(dict(homework_id=hw.id, student_id=student.id,
                                submission_url=f"https://example.com/submissions/{student.admission_number}-{code}.jpg",
                                submitted_at=datetime.now(timezone.utc) - timedelta(hours=rng.randint(1, 20)),
                                status=SubmissionStatus.SUBMITTED, remarks=None))
                        # remaining students: no submission row (PENDING state)
        for i in range(0, len(submission_rows), CHUNK_SIZE):
            await session.execute(insert(HomeworkSubmission), submission_rows[i:i + CHUNK_SIZE])
        print(f"seed_prod (demo dataset): {homework_rows} homework, {len(submission_rows)} submissions")

        # ── Timetable: every section gets a full Mon-Sat grid at its tier's
        # period density. Each slot's subject maps to a fixed role_teacher;
        # a global (staff_id, day, period) set guards against double-booking.
        # If a slot's regular teacher is already busy (rare given the load
        # cap, but possible), fall back to a free floating teacher with
        # is_substitute=True — this also organically demonstrates the
        # substitute-assignment feature the floating teachers exist for.
        used_slots: set[tuple[int, str, int]] = set()
        timetable_rows: list[dict] = []
        substitute_count = 0
        for sec_index, (cname, cls) in enumerate(classes.items()):
            tier = _tier(cls.numeric_order)
            codes, periods_per_day = TIER_SUBJECTS[tier]
            for si, sec_name in enumerate(SECTION_NAMES):
                sec = sections_by_class[cls.id][sec_name]
                offset = (cls.numeric_order * 31 + si * 13) % len(codes)
                idx = 0
                for day in DAYS:
                    for period in range(1, periods_per_day + 1):
                        placed = False
                        for attempt in range(len(codes)):
                            code = codes[(idx + offset + attempt) % len(codes)]
                            teacher = role_teacher[(cname, code)]
                            key = (teacher.id, day, period)
                            if key not in used_slots:
                                used_slots.add(key)
                                timetable_rows.append(dict(class_id=cls.id, section_id=sec.id,
                                    day_of_week=day, period_number=period,
                                    subject_id=subjects_by_code[code].id, staff_id=teacher.id,
                                    is_substitute=False))
                                placed = True
                                break
                        if not placed:
                            # every candidate subject's teacher is busy this slot —
                            # fall back to whichever floating teacher is free.
                            code = codes[idx % len(codes)]
                            sub = next((f for f in floating if (f.id, day, period) not in used_slots), None)
                            if sub is None:
                                sub = min(floating, key=lambda f: sum(
                                    1 for k in used_slots if k[0] == f.id))
                            used_slots.add((sub.id, day, period))
                            timetable_rows.append(dict(class_id=cls.id, section_id=sec.id,
                                day_of_week=day, period_number=period,
                                subject_id=subjects_by_code[code].id, staff_id=sub.id,
                                is_substitute=True))
                            substitute_count += 1
                        idx += 1
        for i in range(0, len(timetable_rows), CHUNK_SIZE):
            await session.execute(insert(TimetableSlot), timetable_rows[i:i + CHUNK_SIZE])
        print(f"seed_prod (demo dataset): {len(timetable_rows)} timetable slots "
              f"({substitute_count} substitute fallbacks)")

        # ── Notices: mixed audience, spread across several different classes.
        now = datetime.now(timezone.utc)
        notice_targets = list(classes.values())
        notices = [
            Notice(title="School Reopening after Summer Vacation",
                content="Classes resume Monday. Please collect syllabus folders from the office.",
                audience=NoticeAudience.EVERYONE, channels=["website", "app"],
                published_at=now - timedelta(days=28), created_by_id=None),
            Notice(title="Annual Sports Day",
                content="Annual Sports Day will be held next month. Details to follow.",
                audience=NoticeAudience.EVERYONE, channels=["website", "app"],
                published_at=now - timedelta(days=14), created_by_id=None),
            Notice(title="PTA Meeting Schedule",
                content="Parent-Teacher meetings are scheduled for all classes this month.",
                audience=NoticeAudience.EVERYONE, channels=["app", "whatsapp"],
                published_at=now - timedelta(hours=6), created_by_id=None),
            Notice(title="Staff Meeting — Friday 4 PM",
                content="All teaching staff to attend the monthly review meeting.",
                audience=NoticeAudience.STAFF, channels=["app"],
                published_at=now - timedelta(days=2), created_by_id=None),
            Notice(title="Staff Training Workshop",
                content="A workshop on the new grading rubric will be held for all staff.",
                audience=NoticeAudience.STAFF, channels=["app"],
                published_at=now - timedelta(days=9), created_by_id=None),
            Notice(title="Staff ID Card Renewal",
                content="Please collect renewed ID cards from the admin office.",
                audience=NoticeAudience.STAFF, channels=["app"],
                published_at=now - timedelta(days=18), created_by_id=None),
        ]
        for i in range(8):
            cls = notice_targets[rng.randrange(len(notice_targets))]
            notices.append(Notice(
                title=f"{cls.name} Datesheet / Activity Update",
                content=f"An important update for {cls.name} students has been shared with class teachers.",
                audience=NoticeAudience.CLASS, target_class_id=cls.id, channels=["app", "whatsapp"],
                published_at=now - timedelta(days=rng.randint(1, 25)), created_by_id=None,
            ))
        session.add_all(notices)

        # ── Admission enquiries: spread across all 5 stages and many levels.
        statuses = list(EnquiryStatus)
        enquiries = []
        for i in range(18):
            status = statuses[i % len(statuses)]
            cname = rng.choice(CLASS_NAMES)
            first = rng.choice(FEMALE_FIRST + MALE_FIRST)
            last = rng.choice(SURNAMES)
            parent_first = rng.choice(FEMALE_FIRST + MALE_FIRST)
            enquiries.append(AdmissionEnquiry(
                child_name=f"{first} {last}", dob=date(2010 + rng.randint(0, 15), rng.randint(1, 12), rng.randint(1, 28)),
                class_applying=cname, parent_name=f"{parent_first} {last}", phone=_phone(rng),
                email=f"{parent_first.lower()}.{last.lower()}{i}@example.com",
                address=_address(rng), source=rng.choice(["website", "referral", "walk-in"]),
                status=status, message=f"Interested in admission for {cname}.",
                notes="Follow-up in progress." if status in (EnquiryStatus.CONTACTED, EnquiryStatus.VISITED) else None,
            ))
        session.add_all(enquiries)

        # ── Contact messages: mixed read/unread.
        contacts = []
        for i in range(8):
            first = rng.choice(FEMALE_FIRST + MALE_FIRST)
            last = rng.choice(SURNAMES)
            contacts.append(ContactMessage(
                name=f"{first} {last}", email=f"{first.lower()}.{last.lower()}{i}@example.com",
                phone=_phone(rng),
                message=rng.choice([
                    "What are the school timings for the primary section?",
                    "Do you offer transport for our area?",
                    "Could you share the fee structure for this year?",
                    "Is lateral admission available mid-year?",
                    "What documents are required for admission?",
                ]),
                is_read=i < 5,
            ))
        session.add_all(contacts)

        await session.commit()
        print(f"seed_prod (demo dataset): {len(notices)} notices, {len(enquiries)} enquiries, "
              f"{len(contacts)} contact messages — committed")

        _write_credential_files(student_specs, teacher_logins)


def _write_credential_files(student_specs: list[dict], teacher_logins: list[dict]) -> None:
    """Full 300-student list -> STUDENT_CREDENTIALS.csv; admin + all teacher
    logins + a representative student sample -> DEMO_CREDENTIALS.md. Both at
    repo root, both generated (not hand-maintained)."""
    csv_path = REPO_ROOT / "STUDENT_CREDENTIALS.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["admission_number", "password", "first_name", "last_name", "class",
                          "section", "roll_number", "attendance_profile", "fee_profile"])
        for spec in student_specs:
            writer.writerow([f"ADM-{spec['idx']:05d}", STUDENT_PASSWORD, spec["first"], spec["last"],
                              spec["class_name"], spec["section_name"], spec["roll"],
                              spec["attendance_profile"], spec["fee_profile"]])

    # representative sample: 2-3 per level (strong+paid, defaulter/chronic, one average)
    sample: list[dict] = []
    by_level: dict[str, list[dict]] = {}
    for spec in student_specs:
        by_level.setdefault(spec["class_name"], []).append(spec)
    for cname in CLASS_NAMES:
        specs = by_level.get(cname, [])
        picks = [s for s in specs if s["roll"] == 1] + [s for s in specs if s["roll"] == 2]
        third = next((s for s in specs if s["roll"] not in (1, 2)), None)
        if third:
            picks.append(third)
        sample.extend(picks)

    md_path = REPO_ROOT / "DEMO_CREDENTIALS.md"
    lines = [
        "# Demo Login Credentials",
        "",
        "⚠️ **This is demo data for evaluating the platform — not real school data.** "
        "Passwords are intentionally simple and printed in plain text. **Wipe this data "
        "(see below) before entering any real student, staff, or fee information.**",
        "",
        "This file and `STUDENT_CREDENTIALS.csv` (repo root, all 300 students) are "
        "**generated** by `backend/app/scripts/seed_prod.py` — re-run it to regenerate. "
        "Every login uses the institutional ID + password scheme.",
        "",
        "**Boot vs. manual**: only the bootstrap layer (school profile, academic year, "
        "classes/sections, subjects, fee structures, the `admin` login) runs automatically "
        "on every backend boot via `SEED_ON_START`. The full dataset below — teachers, "
        "300 students, attendance, exams, fees, homework, notices, timetable, admissions, "
        "contact messages — does **not** run on boot. Run it once, manually: "
        "`python -m app.scripts.seed_prod` (from `backend/`), pointed at the target database.",
        "",
        "## Admin",
        "",
        "| Login ID | Password |",
        "|---|---|",
        f"| `admin` | `{ADMIN_PASSWORD}` |",
        "",
        "## Teachers (all, including floating/substitute)",
        "",
        "| Login ID | Name | Designation | Subjects |",
        "|---|---|---|---|",
    ]
    for t in teacher_logins:
        tag = " (floating)" if t["floating"] else ""
        lines.append(f"| `{t['login_id']}` | {t['name']}{tag} | {t['designation']} | {t['subjects']} |")
    lines += [
        "",
        f"All teacher logins use password `{TEACHER_PASSWORD}`.",
        "",
        "## Students — representative sample",
        "",
        "One strong-attendance+fully-paid, one chronic-absentee+defaulter, and one "
        "average student per class level. **All 300 students have working logins** — "
        "see `STUDENT_CREDENTIALS.csv` at the repo root for the full list.",
        "",
        f"All student logins use password `{STUDENT_PASSWORD}`.",
        "",
        "| Login ID | Name | Class | Attendance | Fees |",
        "|---|---|---|---|---|",
    ]
    for s in sample:
        lines.append(f"| `ADM-{s['idx']:05d}` | {s['first']} {s['last']} | "
                      f"{s['class_name']}-{s['section_name']} | {s['attendance_profile']} | {s['fee_profile']} |")
    lines += [
        "",
        "**Parents:** no separate parent login — parents sign in with their child's "
        "student ID and password exactly as a student would.",
        "",
        "## Wiping the demo data before real data goes in",
        "",
        "Run this **from your own machine**, pointed at the production database:",
        "",
        "```bash",
        "cd backend",
        "echo 'DATABASE_URL=<paste the production Neon URL here>' >> .env",
        "python -m app.scripts.reset_demo --yes",
        "```",
        "",
        "This deletes every data row but keeps the schema, then re-creates only the "
        "bootstrap layer (school profile, academic year, classes/sections, subjects, "
        "fee structures) and a single `admin` login with a password you choose "
        "interactively. No demo teachers/students/attendance are recreated. Afterward, "
        "also set `SEED_ON_START=false` on Render.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"seed_prod (demo dataset): wrote {csv_path.name} (300 rows) and {md_path.name}")


if __name__ == "__main__":
    import asyncio

    async def _main() -> None:
        await seed_production()
        await seed_demo_dataset()

    asyncio.run(_main())

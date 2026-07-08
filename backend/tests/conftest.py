"""Test fixtures — in-memory-style sqlite DB, dev auth, seeded users.

Environment is configured BEFORE the app is imported because Settings and
the engine are created at import time.
"""

import asyncio
import os
from pathlib import Path

TEST_DB = Path(__file__).parent / "test_school.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key-for-ci-only"
os.environ["SEED_ON_START"] = "false"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, async_session_factory, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.academic import AcademicYear, Class, Section, Subject  # noqa: E402
from app.models.school import School  # noqa: E402
from app.models.staff import Staff, StaffSubjectAssignment  # noqa: E402
from app.models.student import Parent, Student  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

from datetime import date  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    if TEST_DB.exists():
        TEST_DB.unlink()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        session.add(School(name="Test School", address="Test Lane", settings={}))
        session.add(
            AcademicYear(
                label="2026-27",
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                is_current=True,
            )
        )
        cls = Class(name="Class 1", numeric_order=1)
        session.add(cls)
        await session.flush()
        section = Section(name="A", class_id=cls.id)
        subject = Subject(name="Mathematics", code="MAT101")
        session.add_all([section, subject])
        await session.flush()

        staff = Staff(first_name="Tina", last_name="Teacher", phone="9000000001")
        session.add(staff)
        await session.flush()
        session.add(
            StaffSubjectAssignment(
                staff_id=staff.id, subject_id=subject.id, class_id=cls.id, section_id=section.id
            )
        )

        student = Student(
            admission_number="ADM-00001",
            first_name="Sam",
            last_name="Student",
            dob=date(2018, 1, 1),
            gender="male",
            class_id=cls.id,
            section_id=section.id,
            roll_number=1,
        )
        session.add(student)
        await session.flush()
        session.add(
            Parent(name="Pat Parent", phone="9000000002", relation="father", student_id=student.id)
        )

        from app.services.security import hash_password

        password_hash = hash_password(TEST_PASSWORD)
        session.add_all(
            [
                User(
                    login_id="admin",
                    password_hash=password_hash,
                    role=UserRole.SUPER_ADMIN,
                    is_active=True,
                ),
                User(
                    login_id="EMP-001",
                    password_hash=password_hash,
                    role=UserRole.TEACHER,
                    linked_staff_id=staff.id,
                    is_active=True,
                ),
                User(
                    login_id="ADM-00001",
                    password_hash=password_hash,
                    role=UserRole.STUDENT,
                    linked_student_id=student.id,
                    is_active=True,
                ),
            ]
        )
        await session.commit()

    yield

    await engine.dispose()
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


TEST_PASSWORD = "Password@Test1"


def _bearer(user_id: int, role: str) -> dict:
    from app.services.security import create_access_token

    token, _ = create_access_token(user_id, role, token_version=0)
    return {"Authorization": f"Bearer {token}"}


# User ids are deterministic on the fresh test DB (creation order above).
ADMIN = _bearer(1, "super_admin")
TEACHER = _bearer(2, "teacher")
STUDENT = _bearer(3, "student")


@pytest.fixture
def admin_headers():
    return ADMIN


@pytest.fixture
def teacher_headers():
    return TEACHER


@pytest.fixture
def student_headers():
    return STUDENT

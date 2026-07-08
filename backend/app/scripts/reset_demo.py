"""Wipe the demo dataset before the school's real data goes in.

Deletes every data row (students, staff, fees, exams, notices, etc.) but
keeps the schema/migrations intact, then re-runs ONLY the bootstrap layer
(school profile placeholder, current academic year, classes, subjects) —
no demo teachers/students/attendance/etc. You choose the new super-admin
password interactively so it's never printed or committed anywhere.

Run this from your own machine, pointed at the real (production) database
— see DEMO_CREDENTIALS.md for the exact steps. Requires an explicit --yes
flag; refuses to run against sqlite (that's local dev, never production).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import delete

from app.config import settings
from app.database import async_session_factory
from app.models.academic import AcademicYear, Class, Section, Subject
from app.models.admission import AdmissionEnquiry
from app.models.attendance import Attendance, StaffAttendance
from app.models.audit import AuditLog
from app.models.cms import Achievement, GalleryAlbum, GalleryImage, NewsEvent
from app.models.communication import WhatsAppMessageLog
from app.models.contact import ContactMessage
from app.models.exam import Exam, ExamSubject, Mark
from app.models.fee import FeeStructure, FeeTransaction
from app.models.homework import Homework, HomeworkSubmission
from app.models.leave import LeaveApplication
from app.models.notice import Notice
from app.models.school import School
from app.models.staff import Staff, StaffSubjectAssignment
from app.models.student import Parent, Student
from app.models.timetable import TimetableSlot
from app.models.user import User

# Deletion order respects foreign keys (children before parents).
TABLES_IN_DELETE_ORDER = [
    Mark, ExamSubject, Exam,
    HomeworkSubmission, Homework,
    FeeTransaction, FeeStructure,
    Attendance, StaffAttendance,
    TimetableSlot,
    GalleryImage, GalleryAlbum, Achievement, NewsEvent,
    WhatsAppMessageLog,
    LeaveApplication,
    AuditLog,
    Notice,
    AdmissionEnquiry,
    ContactMessage,
    User,
    Parent, Student,
    StaffSubjectAssignment, Staff,
    Section, Class, Subject, AcademicYear,
    School,
]


async def reset_demo(new_admin_password: str) -> None:
    if settings.database_url.startswith("sqlite"):
        print("Refusing to run against a local SQLite database — this is for production only.")
        print("(local dev: just delete backend/school.db and re-run seed.py)")
        sys.exit(1)

    async with async_session_factory() as session:
        for model in TABLES_IN_DELETE_ORDER:
            await session.execute(delete(model))
        await session.commit()
        print(f"Wiped {len(TABLES_IN_DELETE_ORDER)} tables.")

    from app.services.security import hash_password
    from app.scripts.seed_prod import seed_production

    # Re-run bootstrap (school/year/classes/subjects) with a placeholder
    # admin, then immediately overwrite that admin's password with the
    # one the operator just typed in.
    await seed_production()

    async with async_session_factory() as session:
        from sqlalchemy import select

        admin = (
            await session.execute(select(User).where(User.login_id == "admin"))
        ).scalars().first()
        if admin:
            admin.password_hash = hash_password(new_admin_password)
            admin.token_version += 1
            await session.commit()
    print("Done. Sign in as 'admin' with the password you just set.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes", action="store_true", required=True,
        help="Required confirmation flag — this permanently deletes all data.",
    )
    args = parser.parse_args()

    print(f"About to WIPE ALL DATA at: {settings.database_url.split('@')[-1]}")
    confirm = input("Type the database host name above to confirm: ").strip()
    host = settings.database_url.split("@")[-1].split("/")[0]
    if confirm != host:
        print("Confirmation did not match — aborted, nothing was deleted.")
        sys.exit(1)

    password = getpass.getpass("New password for the 'admin' super-admin login: ")
    if len(password) < 8:
        print("Password must be at least 8 characters — aborted.")
        sys.exit(1)

    asyncio.run(reset_demo(password))


if __name__ == "__main__":
    main()

"""Idempotent production seed — safe to run on every boot.

Creates the minimum records a fresh deployment needs (school profile,
current academic year, classes LKG through Class 12, one section each,
core subjects, and a pending super-admin user). Existing rows are never
modified or dropped; each block checks before inserting, so running this
repeatedly (SEED_ON_START=true) is harmless.

The full demo dataset lives in backend/seed.py and is for local SQLite only.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.database import async_session_factory
from app.models.academic import AcademicYear, Class, Section, Subject
from app.models.school import School
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


async def seed_production() -> None:
    async with async_session_factory() as session:
        created: list[str] = []

        school = (await session.execute(select(School))).scalars().first()
        if school is None:
            session.add(
                School(
                    name="Knowledge Development Kindergarten Academy",
                    address="",
                    affiliation_number="",
                    contact_email="",
                    contact_phone="",
                    settings={"allow_online_fees": True, "automation": {}},
                )
            )
            created.append("school")

        year = (
            await session.execute(select(AcademicYear).where(AcademicYear.is_current))
        ).scalars().first()
        if year is None:
            session.add(
                AcademicYear(
                    label="2026-27",
                    start_date=date(2026, 4, 1),
                    end_date=date(2027, 3, 31),
                    is_current=True,
                )
            )
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
                created.append(name)

        existing_codes = {
            s.code for s in (await session.execute(select(Subject))).scalars().all()
        }
        for name, code in SUBJECTS:
            if code not in existing_codes:
                session.add(Subject(name=name, code=code))
                created.append(f"subject {name}")

        from app.services.security import hash_password

        admin = (
            await session.execute(select(User).where(User.login_id == "admin"))
        ).scalars().first()
        if admin is None:
            session.add(
                User(
                    login_id="admin",
                    password_hash=hash_password("Admin@2026"),
                    role=UserRole.SUPER_ADMIN,
                    is_active=True,
                )
            )
            created.append("super_admin user 'admin'")

        await session.commit()
        if created:
            print(f"seed_prod: created {len(created)} records: {', '.join(created[:8])}"
                  + ("…" if len(created) > 8 else ""))
        else:
            print("seed_prod: nothing to do (already seeded)")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_production())

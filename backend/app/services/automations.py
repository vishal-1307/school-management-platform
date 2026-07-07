"""WhatsApp automations (SRS §9.1, FR-9, FR-20/21, 6.5).

Each automation checks its toggle in School.settings["automation"] and then
messages parents via the WhatsApp service. With WhatsApp unconfigured every
message is logged as SKIPPED, so the school can watch the automations work
before adding credentials.

Runs use their own DB session because they execute as background tasks
after the request's session has closed.
"""

from __future__ import annotations

import logging
from datetime import date as date_type

from sqlalchemy import select

from app.database import async_session_factory
from app.models.academic import Class
from app.models.exam import Exam
from app.models.fee import FeeStructure, FeeTransaction
from app.models.notice import Notice, NoticeAudience
from app.models.school import School
from app.models.student import Parent, Student
from app.services import whatsapp

logger = logging.getLogger(__name__)


async def _automation_enabled(db, key: str) -> bool:
    school = (await db.execute(select(School))).scalars().first()
    if school is None:
        return False
    return bool((school.settings or {}).get("automation", {}).get(key, False))


def _parent_phone(parent: Parent) -> str | None:
    return parent.whatsapp_number or parent.phone


async def send_absent_alerts(student_ids: list[int], attendance_date: date_type) -> int:
    """FR-9: alert each absent student's parents. Returns messages attempted."""
    if not student_ids:
        return 0
    sent = 0
    async with async_session_factory() as db:
        try:
            if not await _automation_enabled(db, "absent_alerts"):
                return 0
            students = (
                await db.execute(
                    select(Student).where(Student.id.in_(student_ids))
                )
            ).scalars().all()
            for student in students:
                parents = (
                    await db.execute(select(Parent).where(Parent.student_id == student.id))
                ).scalars().all()
                for parent in parents:
                    phone = _parent_phone(parent)
                    if not phone:
                        continue
                    await whatsapp.send_text_message(
                        db,
                        phone,
                        f"Dear {parent.name}, {student.first_name} {student.last_name} was "
                        f"marked ABSENT on {attendance_date.strftime('%d %b %Y')}. "
                        "Please contact the school office if this is unexpected. "
                        "- Knowledge Academy",
                    )
                    sent += 1
            await db.commit()
        except Exception:
            logger.exception("absent-alert automation failed")
            await db.rollback()
    return sent


async def broadcast_notice(notice_id: int) -> int:
    """FR-20/21: send a notice to the parents of every targeted student."""
    sent = 0
    async with async_session_factory() as db:
        try:
            if not await _automation_enabled(db, "notice_broadcast"):
                return -1  # signals "disabled" to the caller
            notice = await db.get(Notice, notice_id)
            if notice is None:
                return 0

            query = select(Student).where(Student.is_active)
            if notice.audience == NoticeAudience.CLASS and notice.target_class_id:
                query = query.where(Student.class_id == notice.target_class_id)
            students = (await db.execute(query)).scalars().all()

            seen_phones: set[str] = set()
            for student in students:
                parents = (
                    await db.execute(select(Parent).where(Parent.student_id == student.id))
                ).scalars().all()
                for parent in parents:
                    phone = _parent_phone(parent)
                    if not phone or phone in seen_phones:
                        continue
                    seen_phones.add(phone)
                    await whatsapp.send_text_message(
                        db,
                        phone,
                        f"📢 {notice.title}\n\n{notice.content}\n- Knowledge Academy",
                    )
                    sent += 1
            await db.commit()
        except Exception:
            logger.exception("notice broadcast failed")
            await db.rollback()
    return sent


async def send_fee_reminders() -> int:
    """SRS 6.5: remind parents of every student with an overdue balance."""
    sent = 0
    async with async_session_factory() as db:
        try:
            if not await _automation_enabled(db, "fee_reminders"):
                return -1
            today = date_type.today()
            structures = (
                await db.execute(select(FeeStructure).where(FeeStructure.due_date <= today))
            ).scalars().all()
            for structure in structures:
                students = (
                    await db.execute(
                        select(Student).where(
                            Student.class_id == structure.class_id, Student.is_active
                        )
                    )
                ).scalars().all()
                for student in students:
                    paid = sum(
                        t.amount_paid
                        for t in (
                            await db.execute(
                                select(FeeTransaction).where(
                                    FeeTransaction.student_id == student.id,
                                    FeeTransaction.fee_structure_id == structure.id,
                                )
                            )
                        ).scalars().all()
                    )
                    balance = structure.amount - paid
                    if balance <= 0:
                        continue
                    parents = (
                        await db.execute(select(Parent).where(Parent.student_id == student.id))
                    ).scalars().all()
                    for parent in parents:
                        phone = _parent_phone(parent)
                        if not phone:
                            continue
                        await whatsapp.send_text_message(
                            db,
                            phone,
                            f"Dear {parent.name}, a fee balance of ₹{balance:,.0f} "
                            f"({structure.fee_head}) is due for "
                            f"{student.first_name} {student.last_name} since "
                            f"{structure.due_date.strftime('%d %b %Y')}. You can pay online "
                            "from the Student Portal or at the school office. "
                            "- Knowledge Academy",
                        )
                        sent += 1
            await db.commit()
        except Exception:
            logger.exception("fee reminder automation failed")
            await db.rollback()
    return sent


async def notify_results_published(exam_id: int) -> int:
    """SRS 9.1: tell parents the moment results are unlocked."""
    sent = 0
    async with async_session_factory() as db:
        try:
            if not await _automation_enabled(db, "results_notification"):
                return -1
            exam = await db.get(Exam, exam_id)
            if exam is None:
                return 0
            class_ = await db.get(Class, exam.class_id)
            students = (
                await db.execute(
                    select(Student).where(
                        Student.class_id == exam.class_id, Student.is_active
                    )
                )
            ).scalars().all()
            for student in students:
                parents = (
                    await db.execute(select(Parent).where(Parent.student_id == student.id))
                ).scalars().all()
                for parent in parents:
                    phone = _parent_phone(parent)
                    if not phone:
                        continue
                    await whatsapp.send_text_message(
                        db,
                        phone,
                        f"Dear {parent.name}, results for {exam.name} "
                        f"({class_.name if class_ else ''}) have been published. View "
                        f"{student.first_name}'s report card in the Student Portal. "
                        "- Knowledge Academy",
                    )
                    sent += 1
            await db.commit()
        except Exception:
            logger.exception("results notification failed")
            await db.rollback()
    return sent

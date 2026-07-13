"""Role-scoped AI assistant tool definitions.

Every tool handler below calls the *exact same* router handler function (or
the same models/scoping helpers) the ordinary portal endpoints use, with the
real authenticated ``current_user`` — the AI is a new interface over the
existing authorization model, never a new access path around it.

WRITE tools are split into two phases:
  - ``preview`` runs read-only: it resolves names/ids, re-runs the same
    scope guard the mutation would use, and builds the exact confirmation
    text. It NEVER mutates. Returns one of:
      {"status": "ready", "title", "summary", "preview", "resolved_args"}
      {"status": "ambiguous", "message", "matches": [...]}
      {"status": "error", "message"}
  - ``execute`` runs only after the user clicks Confirm (see
    ``app/services/ai/pending.py``); it calls the real mutating handler and
    writes an ``ai_assisted`` audit row on top of whatever the handler
    itself already logs.
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from datetime import date as date_cls
from typing import Any, Awaitable, Callable

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fee import FeeStructure, FeeTransaction
from app.models.staff import Staff, StaffSubjectAssignment
from app.models.student import Student
from app.models.user import User, UserRole
from app.services.audit import log_action

ReadFn = Callable[[AsyncSession, User, dict], Awaitable[Any]]
PreviewFn = Callable[[AsyncSession, User, dict], Awaitable[dict]]
ExecuteFn = Callable[[AsyncSession, User, dict, BackgroundTasks], Awaitable[str]]

# Role groups mirroring the ones the reused router handlers enforce.
ADMIN_ROLES: tuple[UserRole, ...] = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)
MARKER_ROLES: tuple[UserRole, ...] = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN, UserRole.TEACHER)

# Privilege rank for target-vs-caller comparisons (higher = more privileged).
_ROLE_RANK: dict[UserRole, int] = {
    UserRole.SUPER_ADMIN: 3,
    UserRole.OFFICE_ADMIN: 2,
    UserRole.TEACHER: 1,
    UserRole.STUDENT: 0,
    UserRole.PARENT: 0,
}


def outranks_or_equals(target: UserRole, caller: UserRole) -> bool:
    """True if target is at least as privileged as caller (blocks lateral/upward writes)."""
    return _ROLE_RANK.get(target, 0) >= _ROLE_RANK.get(caller, 0)


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    read: ReadFn | None = None
    preview: PreviewFn | None = None
    execute: ExecuteFn | None = None
    # Roles permitted to run this WRITE tool — mirrors the require_role() gate on
    # the reused router handler. Enforced server-side in the orchestration loop
    # and re-checked at /confirm, because the executor calls the handler function
    # directly and so does NOT run FastAPI's require_role dependency.
    write_roles: tuple[UserRole, ...] = ()

    @property
    def is_write(self) -> bool:
        return self.preview is not None

    def allows(self, role: UserRole) -> bool:
        return role in self.write_roles

    def to_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


def _one_time_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ─────────────────────────────────────────────────────────────────────────
# ADMIN — READ
# ─────────────────────────────────────────────────────────────────────────


async def _search_people(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.staff import list_staff
    from app.routers.students import list_students

    query = (args.get("query") or "").strip() or None
    kind = args.get("kind")

    # list_students/list_staff match "query" against one column at a time
    # (first_name ILIKE, last_name ILIKE, ...), so a two-word "First Last"
    # query never matches when first/last are separate columns — the exact
    # same gap the human admin search box has. Rather than changing those
    # shared, already-scoped functions, retry token-by-token here and merge
    # by id so a full name still resolves to the right person.
    search_terms = [query] if query else [None]
    if query and " " in query:
        search_terms.extend(query.split())

    students_by_id: dict[int, dict] = {}
    staff_by_id: dict[int, dict] = {}

    for term in search_terms:
        if kind in (None, "student"):
            resp = await list_students(
                class_id=None, section_id=None, is_active=True, search=term,
                page=1, page_size=20, db=db, current_user=current_user,
            )
            for s in resp.items:
                students_by_id[s.id] = {
                    "kind": "student", "student_id": s.id,
                    "name": f"{s.first_name} {s.last_name}",
                    "admission_number": s.admission_number,
                    "class_id": s.class_id, "section_id": s.section_id,
                }

        if kind in (None, "staff"):
            staff_list = await list_staff(is_active=True, search=term, db=db, current_user=current_user)
            for st in staff_list:
                staff_by_id[st.id] = {
                    "kind": "staff", "staff_id": st.id,
                    "name": f"{st.first_name} {st.last_name}", "phone": st.phone,
                }

        if students_by_id or staff_by_id:
            break  # the plain full-string search already matched — no need to fall back

    return {"matches": [*students_by_id.values(), *staff_by_id.values()]}


async def _get_student_fee_status(db: AsyncSession, current_user: User, args: dict) -> Any:
    # Data minimization (SRS: never send more student financial detail to the
    # third-party model than the question needs): default to a due/no-due
    # summary; only include the full per-fee-head breakdown when the caller
    # explicitly asks for it (detail=true) — e.g. "give me the breakdown".
    student = await db.get(Student, args["student_id"])
    if not student:
        return {"error": "not_found", "message": f"No student with id {args['student_id']}"}

    structures = (
        await db.execute(select(FeeStructure).where(FeeStructure.class_id == student.class_id))
    ).scalars().all()

    items = []
    total_balance = 0.0
    for structure in structures:
        paid = (
            await db.execute(
                select(func.coalesce(func.sum(FeeTransaction.amount_paid), 0)).where(
                    FeeTransaction.student_id == student.id,
                    FeeTransaction.fee_structure_id == structure.id,
                )
            )
        ).scalar() or 0
        balance = max(0.0, structure.amount - float(paid))
        total_balance += balance
        items.append({
            "fee_head": structure.fee_head, "amount": structure.amount,
            "paid": float(paid), "balance": balance,
            "due_date": structure.due_date.isoformat(),
        })

    summary = {
        "student_id": student.id,
        "student_name": f"{student.first_name} {student.last_name}",
        "has_dues": total_balance > 0,
        "total_balance": round(total_balance, 2),
    }
    if args.get("detail"):
        summary["items"] = items
    return summary


async def _get_student_attendance(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.attendance import get_attendance_history

    student_id = args["student_id"]
    student = await db.get(Student, student_id)
    if not student:
        return {"error": "not_found", "message": f"No student with id {student_id}"}

    records = await get_attendance_history(
        class_id=None, section_id=None, student_id=student_id,
        date_from=None, date_to=None, attendance_date=None,
        db=db, current_user=current_user,
    )
    total = len(records)
    present = sum(1 for r in records if r.status in ("present", "late"))
    return {
        "student_id": student_id,
        "student_name": f"{student.first_name} {student.last_name}",
        "total_records": total, "present": present,
        "percentage": round(present / total * 100, 1) if total else None,
    }


async def _get_dashboard_summary(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.reports import dashboard_summary

    resp = await dashboard_summary(db=db, current_user=current_user)
    return resp.model_dump()


async def _list_fee_defaulters(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.fees import get_defaulters

    resp = await get_defaulters(
        class_id=args.get("class_id"), academic_year_id=None, as_of_date=None,
        db=db, current_user=current_user,
    )
    if args.get("detail"):
        return {"defaulters": [d.model_dump() for d in resp]}

    # Data minimization: get_defaulters returns one row per unpaid fee head,
    # so a class can be dozens of rows of financial detail (amount_due,
    # amount_paid, due_date per head) for one bulk question ("who owes fees
    # this class"). Default to one row per student with a total balance —
    # full per-fee-head figures only if the admin explicitly asks (detail=true).
    by_student: dict[int, dict] = {}
    for d in resp:
        row = by_student.setdefault(d.student_id, {
            "student_id": d.student_id, "student_name": d.student_name,
            "class_name": d.class_name, "total_balance": 0.0,
        })
        row["total_balance"] += d.balance
    for row in by_student.values():
        row["total_balance"] = round(row["total_balance"], 2)
    return {"defaulter_count": len(by_student), "defaulters": list(by_student.values())}


def _minimize_enquiry(data: dict, include_contact: bool) -> dict:
    # Data minimization: an enquiry pipeline-status question doesn't need the
    # parent's phone/email/address sent to the third-party model — only
    # include them if explicitly asked (e.g. "what's their contact info").
    if include_contact:
        return data
    return {k: v for k, v in data.items() if k not in ("phone", "email", "address")}


async def _get_enquiry_status(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.admissions import get_enquiry, list_enquiries

    include_contact = bool(args.get("detail"))

    if args.get("enquiry_id"):
        try:
            resp = await get_enquiry(args["enquiry_id"], db=db, current_user=current_user)
        except HTTPException as exc:
            return {"error": "not_found", "message": str(exc.detail)}
        return _minimize_enquiry(resp.model_dump(), include_contact)

    name = (args.get("child_name") or "").strip().lower()
    resp = await list_enquiries(status_filter=None, page=1, page_size=100, db=db, current_user=current_user)
    matches = [e for e in resp.items if name in e.child_name.lower()]
    if not matches:
        return {"status": "not_found", "message": f"No enquiry found matching '{args.get('child_name')}'"}
    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "matches": [
                {"enquiry_id": m.id, "child_name": m.child_name, "parent_name": m.parent_name, "status": m.status}
                for m in matches
            ],
        }
    return _minimize_enquiry(matches[0].model_dump(), include_contact)


async def _get_staff_assignments(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.staff import get_staff

    try:
        resp = await get_staff(args["staff_id"], db=db, current_user=current_user)
    except HTTPException as exc:
        return {"error": "not_found", "message": str(exc.detail)}
    return resp.model_dump()


# ─────────────────────────────────────────────────────────────────────────
# ADMIN — WRITE
# ─────────────────────────────────────────────────────────────────────────


async def _preview_deactivate_student(db: AsyncSession, current_user: User, args: dict) -> dict:
    student = await db.get(Student, args["student_id"])
    if not student or not student.is_active:
        return {"status": "error", "message": f"No active student with id {args['student_id']}"}
    return {
        "status": "ready",
        "title": "Deactivate student",
        "summary": (
            f"Deactivate {student.first_name} {student.last_name} "
            f"(admission {student.admission_number}). They lose portal access immediately."
        ),
        "preview": {
            "student_id": student.id,
            "name": f"{student.first_name} {student.last_name}",
            "admission_number": student.admission_number,
        },
        "resolved_args": {"student_id": student.id},
    }


async def _execute_deactivate_student(
    db: AsyncSession, current_user: User, resolved_args: dict, background_tasks: BackgroundTasks
) -> str:
    from app.routers.students import delete_student

    student_id = resolved_args["student_id"]
    resp = await delete_student(student_id, db=db, current_user=current_user)
    await log_action(db, current_user, "ai.student.deactivate", "student", student_id, {"ai_assisted": True})
    return resp.message


async def _preview_reactivate_student(db: AsyncSession, current_user: User, args: dict) -> dict:
    student = await db.get(Student, args["student_id"])
    if not student:
        return {"status": "error", "message": f"No student with id {args['student_id']}"}
    if student.is_active:
        return {"status": "error", "message": f"{student.first_name} {student.last_name} is already active"}
    return {
        "status": "ready",
        "title": "Reactivate student",
        "summary": (
            f"Reactivate {student.first_name} {student.last_name} "
            f"(admission {student.admission_number}). Portal access is restored."
        ),
        "preview": {"student_id": student.id, "name": f"{student.first_name} {student.last_name}"},
        "resolved_args": {"student_id": student.id},
    }


async def _execute_reactivate_student(
    db: AsyncSession, current_user: User, resolved_args: dict, background_tasks: BackgroundTasks
) -> str:
    from app.routers.students import update_student
    from app.schemas.student import StudentUpdate

    student_id = resolved_args["student_id"]
    resp = await update_student(student_id, StudentUpdate(is_active=True), db=db, current_user=current_user)
    await log_action(db, current_user, "ai.student.reactivate", "student", student_id, {"ai_assisted": True})
    return f"{resp.first_name} {resp.last_name} reactivated."


async def _preview_deactivate_staff(db: AsyncSession, current_user: User, args: dict) -> dict:
    staff = await db.get(Staff, args["staff_id"])
    if not staff or not staff.is_active:
        return {"status": "error", "message": f"No active staff with id {args['staff_id']}"}
    return {
        "status": "ready",
        "title": "Deactivate staff",
        "summary": f"Deactivate {staff.first_name} {staff.last_name}. They lose portal access immediately.",
        "preview": {"staff_id": staff.id, "name": f"{staff.first_name} {staff.last_name}"},
        "resolved_args": {"staff_id": staff.id},
    }


async def _execute_deactivate_staff(
    db: AsyncSession, current_user: User, resolved_args: dict, background_tasks: BackgroundTasks
) -> str:
    from app.routers.staff import delete_staff

    staff_id = resolved_args["staff_id"]
    resp = await delete_staff(staff_id, db=db, current_user=current_user)
    await log_action(db, current_user, "ai.staff.deactivate", "staff", staff_id, {"ai_assisted": True})
    return resp.message


async def _resolve_user_account(db: AsyncSession, args: dict) -> User | None:
    if args.get("login_id"):
        result = await db.execute(
            select(User).where(func.lower(User.login_id) == args["login_id"].strip().lower())
        )
        return result.scalar_one_or_none()
    if args.get("student_id"):
        result = await db.execute(select(User).where(User.linked_student_id == args["student_id"]))
        return result.scalar_one_or_none()
    if args.get("staff_id"):
        result = await db.execute(select(User).where(User.linked_staff_id == args["staff_id"]))
        return result.scalar_one_or_none()
    return None


async def _preview_reset_password(db: AsyncSession, current_user: User, args: dict) -> dict:
    user = await _resolve_user_account(db, args)
    if not user:
        return {"status": "error", "message": "No matching user account found for that person"}
    # Defense in depth: even though only SUPER_ADMIN can reach this tool
    # (see write_roles on the ToolSpec below), never let the AI reset a
    # password for an account at or above the caller's own privilege level.
    if outranks_or_equals(user.role, current_user.role):
        return {
            "status": "error",
            "message": "You can't reset a password for an account at or above your own privilege level through the assistant — use the Users & Roles page directly.",
        }
    return {
        "status": "ready",
        "title": "Reset password",
        "summary": (
            f"Reset the password for login '{user.login_id}' ({user.role.value}). "
            "A new one-time password will be generated and shown once after you confirm — "
            "share it with them securely. Their other sessions will be signed out."
        ),
        "preview": {"user_id": user.id, "login_id": user.login_id, "role": user.role.value},
        "resolved_args": {"user_id": user.id, "login_id": user.login_id},
    }


async def _execute_reset_password(
    db: AsyncSession, current_user: User, resolved_args: dict, background_tasks: BackgroundTasks
) -> str:
    from app.routers.users import reset_password
    from app.schemas.user import PasswordReset

    user_id = resolved_args["user_id"]
    login_id = resolved_args.get("login_id")
    new_password = _one_time_password()
    await reset_password(user_id, PasswordReset(password=new_password), db=db, current_user=current_user)
    # reset_password() already writes its own "user.reset_password" audit row
    # (no detail dict — see routers/users.py) so the password is never logged
    # there either. This adds a second, ai-tagged row for provenance only.
    await log_action(
        db, current_user, "ai.user.reset_password", "user", user_id,
        {"ai_assisted": True, "target_login_id": login_id},
    )
    return f"Password reset for '{login_id}'. New one-time password: {new_password} — share it securely; it will not be shown again."


ADMIN_TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="search_people", read=_search_people,
        description="Search students and/or staff by name or admission number. Use this first to resolve a name to an id before any other admin tool.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Name or admission number to search for"},
                "kind": {"type": "string", "enum": ["student", "staff"], "description": "Restrict to one kind; omit to search both"},
            },
            "required": ["query"],
        },
    ),
    ToolSpec(
        name="get_student_fee_status", read=_get_student_fee_status,
        description=(
            "Get whether a student has outstanding fee dues and the total balance. "
            "Pass detail=true only if the admin explicitly asks for a fee-head-by-fee-head breakdown."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"},
                "detail": {"type": "boolean", "description": "Include the full per-fee-head breakdown"},
            },
            "required": ["student_id"],
        },
    ),
    ToolSpec(
        name="get_student_attendance", read=_get_student_attendance,
        description="Get a student's overall attendance percentage and record count.",
        input_schema={"type": "object", "properties": {"student_id": {"type": "integer"}}, "required": ["student_id"]},
    ),
    ToolSpec(
        name="get_dashboard_summary", read=_get_dashboard_summary,
        description="Get the admin dashboard's headline numbers (students, staff, fee collection, attendance today, etc).",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="list_fee_defaulters", read=_list_fee_defaulters,
        description=(
            "List students with unpaid or partially paid fees, optionally filtered by class. "
            "Pass detail=true only if the admin explicitly asks for a fee-head-by-fee-head breakdown."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "class_id": {"type": "integer"},
                "detail": {"type": "boolean", "description": "Include the full per-fee-head breakdown"},
            },
        },
    ),
    ToolSpec(
        name="get_enquiry_status", read=_get_enquiry_status,
        description=(
            "Look up an admission enquiry's pipeline status by child name or enquiry id. "
            "Pass detail=true only if the admin explicitly asks for the parent's contact info."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "child_name": {"type": "string"}, "enquiry_id": {"type": "integer"},
                "detail": {"type": "boolean", "description": "Include parent phone/email/address"},
            },
        },
    ),
    ToolSpec(
        name="get_staff_assignments", read=_get_staff_assignments,
        description="Get a staff member's subject/class/section teaching assignments.",
        input_schema={"type": "object", "properties": {"staff_id": {"type": "integer"}}, "required": ["staff_id"]},
    ),
    ToolSpec(
        name="deactivate_student", preview=_preview_deactivate_student, execute=_execute_deactivate_student,
        description="Deactivate (soft-delete) a student, revoking their portal access. Requires confirmation.",
        input_schema={"type": "object", "properties": {"student_id": {"type": "integer"}}, "required": ["student_id"]},
        # delete_student (students.py) is require_role(SUPER_ADMIN) — match it exactly,
        # since the executor calls that handler directly and bypasses its own dependency.
        write_roles=(UserRole.SUPER_ADMIN,),
    ),
    ToolSpec(
        name="reactivate_student", preview=_preview_reactivate_student, execute=_execute_reactivate_student,
        description="Reactivate a previously deactivated student. Requires confirmation.",
        input_schema={"type": "object", "properties": {"student_id": {"type": "integer"}}, "required": ["student_id"]},
        # update_student (students.py) is require_role(*ADMIN_ROLES).
        write_roles=ADMIN_ROLES,
    ),
    ToolSpec(
        name="deactivate_staff", preview=_preview_deactivate_staff, execute=_execute_deactivate_staff,
        description="Deactivate (soft-delete) a staff member, revoking their portal access. Requires confirmation.",
        input_schema={"type": "object", "properties": {"staff_id": {"type": "integer"}}, "required": ["staff_id"]},
        # delete_staff (staff.py) is require_role(SUPER_ADMIN).
        write_roles=(UserRole.SUPER_ADMIN,),
    ),
    ToolSpec(
        name="reset_user_password", preview=_preview_reset_password, execute=_execute_reset_password,
        description=(
            "Reset a user's login password to a freshly generated one-time password. "
            "Identify the target by student_id, staff_id, or login_id (get these from search_people). Requires confirmation."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"}, "staff_id": {"type": "integer"}, "login_id": {"type": "string"},
            },
        },
        # reset_password (users.py) is require_role(SUPER_ADMIN).
        write_roles=(UserRole.SUPER_ADMIN,),
    ),
]


# ─────────────────────────────────────────────────────────────────────────
# TEACHER — READ
# ─────────────────────────────────────────────────────────────────────────


async def _get_my_classes(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.staff import get_my_dashboard

    dash = await get_my_dashboard(db=db, current_user=current_user)
    return {"classes": [c.model_dump() for c in dash.my_classes]}


async def _get_today_schedule(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.staff import get_my_dashboard

    dash = await get_my_dashboard(db=db, current_user=current_user)
    return {"schedule": [p.model_dump() for p in dash.today_schedule]}


async def _get_class_roster(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.students import list_students

    try:
        resp = await list_students(
            class_id=args["class_id"], section_id=args["section_id"], is_active=True,
            search=None, page=1, page_size=200, db=db, current_user=current_user,
        )
    except HTTPException as exc:
        return {"error": "forbidden" if exc.status_code == 403 else "error", "message": str(exc.detail)}
    return {
        "roster": [
            {"student_id": s.id, "name": f"{s.first_name} {s.last_name}", "roll_number": s.roll_number,
             "admission_number": s.admission_number}
            for s in resp.items
        ]
    }


async def _get_student_attendance_in_my_class(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.attendance import get_attendance_history

    try:
        records = await get_attendance_history(
            class_id=args["class_id"], section_id=args["section_id"], student_id=args["student_id"],
            date_from=None, date_to=None, attendance_date=None, db=db, current_user=current_user,
        )
    except HTTPException as exc:
        return {"error": "forbidden" if exc.status_code == 403 else "error", "message": str(exc.detail)}
    total = len(records)
    present = sum(1 for r in records if r.status in ("present", "late"))
    return {
        "student_id": args["student_id"], "total_records": total, "present": present,
        "percentage": round(present / total * 100, 1) if total else None,
    }


async def _get_student_marks_in_my_class(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.exams import list_marks

    try:
        marks = await list_marks(exam_subject_id=args["exam_subject_id"], db=db, current_user=current_user)
    except HTTPException as exc:
        return {"error": "forbidden" if exc.status_code == 403 else "error", "message": str(exc.detail)}
    match = next((m for m in marks if m["student_id"] == args["student_id"]), None)
    if not match:
        return {"status": "not_found", "message": "No marks entry found for that student in this exam subject."}
    return match


# ─────────────────────────────────────────────────────────────────────────
# TEACHER — WRITE: mark_class_attendance
# ─────────────────────────────────────────────────────────────────────────


async def _teacher_class_options(db: AsyncSession, current_user: User) -> list[dict]:
    result = await db.execute(
        select(StaffSubjectAssignment)
        .options(selectinload(StaffSubjectAssignment.class_), selectinload(StaffSubjectAssignment.section))
        .where(StaffSubjectAssignment.staff_id == current_user.linked_staff_id)
    )
    seen: dict[tuple[int, int], dict] = {}
    for a in result.scalars().all():
        key = (a.class_id, a.section_id)
        if key not in seen:
            seen[key] = {
                "class_id": a.class_id, "section_id": a.section_id,
                "class_name": a.class_.name if a.class_ else "",
                "section_name": a.section.name if a.section else "",
            }
    return list(seen.values())


async def _preview_mark_attendance(db: AsyncSession, current_user: User, args: dict) -> dict:
    from app.routers.students import list_students

    options = await _teacher_class_options(db, current_user)
    if not options:
        return {"status": "error", "message": "You have no assigned classes."}

    class_id = args.get("class_id")
    section_id = args.get("section_id")
    if class_id is None or section_id is None:
        if len(options) > 1:
            return {
                "status": "ambiguous",
                "message": "You teach more than one class/section — which one should I mark attendance for?",
                "matches": options,
            }
        class_id = options[0]["class_id"]
        section_id = options[0]["section_id"]
    elif not any(o["class_id"] == class_id and o["section_id"] == section_id for o in options):
        return {"status": "error", "message": "You are not assigned to that class/section."}

    class_option = next(o for o in options if o["class_id"] == class_id and o["section_id"] == section_id)

    raw_date = args.get("date")
    attendance_date = date_cls.fromisoformat(raw_date) if raw_date else date_cls.today()

    roster_resp = await list_students(
        class_id=class_id, section_id=section_id, is_active=True,
        search=None, page=1, page_size=200, db=db, current_user=current_user,
    )
    roster = roster_resp.items
    if not roster:
        return {"status": "error", "message": "No active students found in that class/section."}

    absent_ids: set[int] = set()
    for raw_name in args.get("absent_student_names", []) or []:
        name = raw_name.strip().lower()
        if not name:
            continue
        matches = [s for s in roster if name in f"{s.first_name} {s.last_name}".lower()]
        if not matches:
            return {"status": "error", "message": f"No student named '{raw_name}' found in this class/section roster."}
        if len(matches) > 1:
            return {
                "status": "ambiguous",
                "message": f"Multiple students match '{raw_name}' — which one did you mean?",
                "matches": [
                    {"student_id": s.id, "name": f"{s.first_name} {s.last_name}", "roll_number": s.roll_number}
                    for s in matches
                ],
            }
        absent_ids.add(matches[0].id)

    entries = [{"student_id": s.id, "status": "absent" if s.id in absent_ids else "present"} for s in roster]
    full_roster_preview = [
        {"student_id": s.id, "name": f"{s.first_name} {s.last_name}", "roll_number": s.roll_number,
         "status": "absent" if s.id in absent_ids else "present"}
        for s in roster
    ]

    return {
        "status": "ready",
        "title": "Mark attendance",
        "summary": (
            f"Mark attendance for {class_option['class_name']}-{class_option['section_name']} on "
            f"{attendance_date.isoformat()}: {len(roster) - len(absent_ids)} present, {len(absent_ids)} absent."
        ),
        "preview": {
            "class_name": class_option["class_name"], "section_name": class_option["section_name"],
            "date": attendance_date.isoformat(), "roster": full_roster_preview,
        },
        "resolved_args": {
            "class_id": class_id, "section_id": section_id,
            "date": attendance_date.isoformat(), "entries": entries,
        },
    }


async def _execute_mark_attendance(
    db: AsyncSession, current_user: User, resolved_args: dict, background_tasks: BackgroundTasks
) -> str:
    from app.routers.attendance import mark_attendance
    from app.schemas.attendance import AttendanceMarkRequest, StudentAttendanceEntry

    payload = AttendanceMarkRequest(
        class_id=resolved_args["class_id"],
        section_id=resolved_args["section_id"],
        date=date_cls.fromisoformat(resolved_args["date"]),
        period=None,
        entries=[StudentAttendanceEntry(**e) for e in resolved_args["entries"]],
    )
    resp = await mark_attendance(payload, background_tasks, db=db, current_user=current_user)
    await log_action(
        db, current_user, "ai.attendance.mark", "class", resolved_args["class_id"],
        {
            "ai_assisted": True, "section_id": resolved_args["section_id"],
            "date": resolved_args["date"], "entries_count": len(resolved_args["entries"]),
        },
    )
    return resp.message


TEACHER_TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="get_my_classes", read=_get_my_classes,
        description="List the classes/sections/subjects I am assigned to teach.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_today_schedule", read=_get_today_schedule,
        description="Get today's teaching schedule (periods, subjects, classes).",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_class_roster", read=_get_class_roster,
        description="List the students in one of my assigned class/sections.",
        input_schema={
            "type": "object",
            "properties": {"class_id": {"type": "integer"}, "section_id": {"type": "integer"}},
            "required": ["class_id", "section_id"],
        },
    ),
    ToolSpec(
        name="get_student_attendance_in_my_class", read=_get_student_attendance_in_my_class,
        description="Get one student's attendance percentage, scoped to one of my assigned class/sections.",
        input_schema={
            "type": "object",
            "properties": {
                "student_id": {"type": "integer"}, "class_id": {"type": "integer"}, "section_id": {"type": "integer"},
            },
            "required": ["student_id", "class_id", "section_id"],
        },
    ),
    ToolSpec(
        name="get_student_marks_in_my_class", read=_get_student_marks_in_my_class,
        description="Get one student's marks for an exam-subject I teach.",
        input_schema={
            "type": "object",
            "properties": {"exam_subject_id": {"type": "integer"}, "student_id": {"type": "integer"}},
            "required": ["exam_subject_id", "student_id"],
        },
    ),
    ToolSpec(
        name="mark_class_attendance", preview=_preview_mark_attendance, execute=_execute_mark_attendance,
        description=(
            "Mark today's (or a given date's) attendance for one of my classes. Pass the names of absent "
            "students only — everyone else in the roster is marked present. If I teach more than one "
            "class/section and don't say which, ask me. Requires confirmation."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "class_id": {"type": "integer"}, "section_id": {"type": "integer"},
                "date": {"type": "string", "description": "YYYY-MM-DD; omit for today"},
                "absent_student_names": {"type": "array", "items": {"type": "string"}},
            },
        },
        # mark_attendance (attendance.py) is require_role(*MARKER_ROLES).
        write_roles=MARKER_ROLES,
    ),
]


# ─────────────────────────────────────────────────────────────────────────
# STUDENT — READ ONLY, self-scoped (no identifying params — identity is
# always current_user.linked_student_id)
# ─────────────────────────────────────────────────────────────────────────


async def _get_my_attendance(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.attendance import my_attendance

    return await my_attendance(date_from=None, date_to=None, db=db, current_user=current_user)


async def _get_my_pending_homework(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.models.homework import Homework, HomeworkSubmission
    from app.routers.homework import list_homework
    from app.routers.students import get_my_student_record

    student = await get_my_student_record(db=db, current_user=current_user)
    homework = await list_homework(
        class_id=student.class_id, section_id=student.section_id, subject_id=None,
        db=db, current_user=current_user,
    )
    submitted_ids = {
        row[0]
        for row in (
            await db.execute(
                select(HomeworkSubmission.homework_id).where(HomeworkSubmission.student_id == student.id)
            )
        ).all()
    }
    pending = [h.model_dump() for h in homework if h.id not in submitted_ids]
    return {"pending_homework": pending, "pending_count": len(pending)}


async def _get_my_results(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.exams import my_published_results

    return {"results": await my_published_results(db=db, current_user=current_user)}


async def _get_my_fee_status(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.fees import my_fee_status

    full = await my_fee_status(db=db, current_user=current_user)
    if args.get("detail"):
        return full
    # Data minimization: default to a due/no-due summary rather than sending
    # every fee item and every past receipt number to the third-party model
    # for what's usually a yes/no question ("do I owe anything").
    total_balance = round(sum(item["balance"] for item in full["items"]), 2)
    return {
        "student_id": full["student_id"],
        "has_dues": total_balance > 0,
        "total_balance": total_balance,
    }


async def _get_my_timetable(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.students import get_my_student_record
    from app.routers.timetable import get_weekly_timetable

    student = await get_my_student_record(db=db, current_user=current_user)
    resp = await get_weekly_timetable(
        class_id=student.class_id, section_id=student.section_id, db=db, current_user=current_user,
    )
    return resp.model_dump()


async def _get_my_notices(db: AsyncSession, current_user: User, args: dict) -> Any:
    from app.routers.students import get_my_dashboard

    dash = await get_my_dashboard(db=db, current_user=current_user)
    return {"notices": [n.model_dump() for n in dash.recent_notices]}


STUDENT_TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="get_my_attendance", read=_get_my_attendance,
        description="Get my own attendance history and percentage.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_my_pending_homework", read=_get_my_pending_homework,
        description="List homework assigned to my class that I have not submitted yet.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_my_results", read=_get_my_results,
        description="Get my published exam results. Never returns anything for an exam whose results are not yet published.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_my_fee_status", read=_get_my_fee_status,
        description=(
            "Get whether I have outstanding fee dues and the total balance. "
            "Pass detail=true only if I explicitly ask for the full item/payment-history breakdown."
        ),
        input_schema={
            "type": "object",
            "properties": {"detail": {"type": "boolean", "description": "Include full items + payment history"}},
        },
    ),
    ToolSpec(
        name="get_my_timetable", read=_get_my_timetable,
        description="Get my weekly class timetable.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="get_my_notices", read=_get_my_notices,
        description="Get recent notices relevant to me.",
        input_schema={"type": "object", "properties": {}},
    ),
]


TOOLS_BY_ROLE: dict[UserRole, list[ToolSpec]] = {
    UserRole.SUPER_ADMIN: ADMIN_TOOLS,
    UserRole.OFFICE_ADMIN: ADMIN_TOOLS,
    UserRole.TEACHER: TEACHER_TOOLS,
    UserRole.STUDENT: STUDENT_TOOLS,
}


def get_tools_for_role(role: UserRole) -> list[ToolSpec]:
    return TOOLS_BY_ROLE.get(role, [])


def get_tool(role: UserRole, name: str) -> ToolSpec | None:
    return next((t for t in get_tools_for_role(role) if t.name == name), None)

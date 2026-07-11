"""Tests for the role-scoped AI assistant.

``ai.client.run_messages`` is patched with a scripted sequence of Anthropic-
shaped responses so these tests are deterministic and need no live API key —
they verify the *tool dispatch, scoping, and confirm-before-write plumbing*,
not the model's judgement.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import and_, select


class ScriptedAssistant:
    """Replaces ai.client.run_messages with a canned sequence of responses."""

    def __init__(self, *responses: dict):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def __call__(self, system, messages, tools, max_tokens: int = 1024) -> dict:
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        return self.responses.pop(0)


def _tool_use(tool_id: str, name: str, input_: dict) -> dict:
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": input_}]}


def _end_turn(text: str) -> dict:
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}


@pytest.fixture
async def ai_enabled(client, admin_headers):
    resp = await client.put(
        "/api/settings/features", headers=admin_headers, json={"ai_assistant_enabled": True}
    )
    assert resp.status_code == 200
    yield
    await client.put(
        "/api/settings/features", headers=admin_headers, json={"ai_assistant_enabled": False}
    )


# ── Gating ───────────────────────────────────────────────────────────────


async def test_chat_403_when_disabled(client, admin_headers):
    """Default off: the flag isn't touched here, so this must 403."""
    response = await client.post(
        "/api/ai/assistant/chat",
        headers=admin_headers,
        json={"transcript": [{"role": "user", "text": "hi"}]},
    )
    assert response.status_code == 403


# ── Structural: role toolsets are partitioned server-side ───────────────


def test_student_toolset_is_read_only_and_takes_no_identifying_params():
    from app.models.user import UserRole
    from app.services.ai.tools import get_tools_for_role

    tools = get_tools_for_role(UserRole.STUDENT)
    assert len(tools) == 6
    for tool in tools:
        assert not tool.is_write, f"{tool.name} must be read-only for students"
        # No tool may accept a student_id (or any) parameter — identity is
        # always current_user.linked_student_id, never a client-supplied id.
        assert tool.input_schema.get("properties", {}) == {}


def test_teacher_and_student_toolsets_have_no_admin_tools():
    from app.models.user import UserRole
    from app.services.ai.tools import ADMIN_TOOLS, get_tools_for_role

    admin_names = {t.name for t in ADMIN_TOOLS}
    for role in (UserRole.TEACHER, UserRole.STUDENT):
        names = {t.name for t in get_tools_for_role(role)}
        assert names.isdisjoint(admin_names)

    # Teacher's only write tool is attendance marking, never a deactivate/reset tool.
    teacher_writes = {t.name for t in get_tools_for_role(UserRole.TEACHER) if t.is_write}
    assert teacher_writes == {"mark_class_attendance"}


# ── Teacher cross-scope refusal ──────────────────────────────────────────


async def test_teacher_cannot_read_unassigned_class_roster(client, teacher_headers, ai_enabled, monkeypatch):
    scripted = ScriptedAssistant(
        _tool_use("t1", "get_class_roster", {"class_id": 999, "section_id": 999}),
        _end_turn("You're not assigned to that class."),
    )
    monkeypatch.setattr("app.services.ai.assistant.run_messages", scripted)

    response = await client.post(
        "/api/ai/assistant/chat",
        headers=teacher_headers,
        json={"transcript": [{"role": "user", "text": "show me class 999's roster"}]},
    )
    assert response.status_code == 200
    assert "not assigned" in response.json()["reply"].lower()

    # The tool itself must have reported the 403 from the real scoping guard —
    # never silently returned data or a different error shape.
    tool_result = scripted.calls[1]["messages"][-1]["content"][0]["content"]
    assert "forbidden" in tool_result


# ── Student cannot see an unpublished result (FR-16) ─────────────────────


async def test_student_cannot_see_unpublished_result(
    client, admin_headers, student_headers, ai_enabled, monkeypatch
):
    exam = await client.post(
        "/api/exams/",
        headers=admin_headers,
        json={
            "name": "AI Assistant Unpublished Exam",
            "academic_year_id": 1,
            "class_id": 1,
            "exam_type": "Unit Test",
            "start_date": "2026-08-01",
            "end_date": "2026-08-05",
            "subjects": [{"subject_id": 1, "max_marks": 100, "passing_marks": 33}],
        },
    )
    assert exam.status_code in (200, 201)

    scripted = ScriptedAssistant(
        _tool_use("t1", "get_my_results", {}),
        _end_turn("You have no published results yet."),
    )
    monkeypatch.setattr("app.services.ai.assistant.run_messages", scripted)

    response = await client.post(
        "/api/ai/assistant/chat",
        headers=student_headers,
        json={"transcript": [{"role": "user", "text": "what are my results?"}]},
    )
    assert response.status_code == 200
    tool_result = scripted.calls[1]["messages"][-1]["content"][0]["content"]
    assert "AI Assistant Unpublished Exam" not in tool_result


# ── Confirm-before-write: admin deactivate + audit ───────────────────────


async def test_deactivate_student_blocks_until_confirmed_and_audits(
    client, admin_headers, ai_enabled, monkeypatch
):
    created = await client.post(
        "/api/students/",
        headers=admin_headers,
        json={
            "first_name": "Throwaway", "last_name": "Kid", "dob": "2018-03-03", "gender": "male",
            "class_id": 1, "section_id": 1, "roll_number": 50,
        },
    )
    assert created.status_code == 201
    student_id = created.json()["id"]

    scripted = ScriptedAssistant(_tool_use("t1", "deactivate_student", {"student_id": student_id}))
    monkeypatch.setattr("app.services.ai.assistant.run_messages", scripted)

    chat = await client.post(
        "/api/ai/assistant/chat",
        headers=admin_headers,
        json={"transcript": [{"role": "user", "text": f"deactivate student {student_id}"}]},
    )
    assert chat.status_code == 200
    pending = chat.json()["pending_action"]
    assert pending is not None
    assert pending["preview"]["student_id"] == student_id

    # Phase 1 must never mutate.
    still_active = await client.get(f"/api/students/{student_id}", headers=admin_headers)
    assert still_active.json()["is_active"] is True

    # A different user cannot confirm someone else's pending action.
    from tests.conftest import TEACHER

    denied = await client.post(
        "/api/ai/assistant/confirm", headers=TEACHER, json={"action_id": pending["action_id"]}
    )
    assert denied.status_code == 404

    confirm = await client.post(
        "/api/ai/assistant/confirm", headers=admin_headers, json={"action_id": pending["action_id"]}
    )
    assert confirm.status_code == 200

    now_inactive = await client.get(f"/api/students/{student_id}", headers=admin_headers)
    assert now_inactive.json()["is_active"] is False

    # A second confirm of the same (now-discarded) action is refused.
    replay = await client.post(
        "/api/ai/assistant/confirm", headers=admin_headers, json={"action_id": pending["action_id"]}
    )
    assert replay.status_code == 404

    log = await client.get("/api/users/audit-log?page_size=200", headers=admin_headers)
    row = next(
        r for r in log.json()
        if r["action"] == "ai.student.deactivate" and r["entity_id"] == student_id
    )
    assert row["detail"]["ai_assisted"] is True


async def test_cancel_discards_pending_action(client, admin_headers, ai_enabled, monkeypatch):
    created = await client.post(
        "/api/students/",
        headers=admin_headers,
        json={
            "first_name": "Cancelme", "last_name": "Kid", "dob": "2018-04-04", "gender": "male",
            "class_id": 1, "section_id": 1, "roll_number": 51,
        },
    )
    student_id = created.json()["id"]

    scripted = ScriptedAssistant(_tool_use("t1", "deactivate_student", {"student_id": student_id}))
    monkeypatch.setattr("app.services.ai.assistant.run_messages", scripted)
    chat = await client.post(
        "/api/ai/assistant/chat",
        headers=admin_headers,
        json={"transcript": [{"role": "user", "text": f"deactivate student {student_id}"}]},
    )
    action_id = chat.json()["pending_action"]["action_id"]

    cancelled = await client.post("/api/ai/assistant/cancel", headers=admin_headers, json={"action_id": action_id})
    assert cancelled.status_code == 200

    confirm_after_cancel = await client.post(
        "/api/ai/assistant/confirm", headers=admin_headers, json={"action_id": action_id}
    )
    assert confirm_after_cancel.status_code == 404

    still_active = await client.get(f"/api/students/{student_id}", headers=admin_headers)
    assert still_active.json()["is_active"] is True


# ── Reset password: never logs the plaintext, works end to end ──────────


async def test_reset_password_never_logs_plaintext(client, admin_headers, ai_enabled, monkeypatch):
    created = await client.post(
        "/api/users/",
        headers=admin_headers,
        json={"login_id": "AI-RESET-1", "password": "OldPassword@1", "role": "teacher"},
    )
    assert created.status_code == 201

    scripted = ScriptedAssistant(_tool_use("t1", "reset_user_password", {"login_id": "AI-RESET-1"}))
    monkeypatch.setattr("app.services.ai.assistant.run_messages", scripted)
    chat = await client.post(
        "/api/ai/assistant/chat",
        headers=admin_headers,
        json={"transcript": [{"role": "user", "text": "reset the password for AI-RESET-1"}]},
    )
    action_id = chat.json()["pending_action"]["action_id"]

    confirm = await client.post(
        "/api/ai/assistant/confirm", headers=admin_headers, json={"action_id": action_id}
    )
    assert confirm.status_code == 200
    reply = confirm.json()["reply"]
    assert "New one-time password:" in reply
    new_password = reply.split("New one-time password:")[1].split("—")[0].strip()

    # The new password actually works.
    login = await client.post(
        "/api/auth/login", json={"login_id": "AI-RESET-1", "password": new_password}
    )
    assert login.status_code == 200

    # Every audit row for this action is free of the plaintext password.
    log = await client.get("/api/users/audit-log?page_size=200", headers=admin_headers)
    ai_rows = [r for r in log.json() if r["action"] == "ai.user.reset_password"]
    assert ai_rows, "expected an ai.user.reset_password audit row"
    for row in ai_rows:
        assert row["detail"]["ai_assisted"] is True
        assert new_password not in str(row["detail"])
    manual_rows = [r for r in log.json() if r["action"] == "user.reset_password"]
    for row in manual_rows:
        assert row["detail"] is None or new_password not in str(row["detail"])


# ── mark_class_attendance: ambiguity never guesses ───────────────────────


async def test_mark_attendance_ambiguous_name_returns_matches():
    """Unit-tests the pure resolver directly, per the plan's verification spec."""
    from app.database import async_session_factory
    from app.models.academic import Class, Section
    from app.models.staff import Staff, StaffSubjectAssignment
    from app.models.student import Student
    from app.models.user import User, UserRole
    from app.services.ai.tools import _preview_mark_attendance

    async with async_session_factory() as db:
        cls = Class(name="AI Ambiguity Class", numeric_order=999)
        db.add(cls)
        await db.flush()
        section = Section(name="Z", class_id=cls.id)
        staff = Staff(first_name="Amb", last_name="Teacher", phone="9000009999")
        db.add_all([section, staff])
        await db.flush()
        db.add(StaffSubjectAssignment(staff_id=staff.id, subject_id=1, class_id=cls.id, section_id=section.id))
        db.add_all([
            Student(
                admission_number="ADM-AMB1", first_name="Sam", last_name="Student",
                dob=date(2018, 1, 1), gender="male", class_id=cls.id, section_id=section.id, roll_number=1,
            ),
            Student(
                admission_number="ADM-AMB2", first_name="Sam", last_name="Studentson",
                dob=date(2018, 1, 1), gender="male", class_id=cls.id, section_id=section.id, roll_number=2,
            ),
        ])
        await db.flush()

        fake_teacher = User(
            login_id="tmp-amb", password_hash="x", role=UserRole.TEACHER,
            linked_staff_id=staff.id, is_active=True,
        )

        result = await _preview_mark_attendance(db, fake_teacher, {"absent_student_names": ["Sam"]})
        assert result["status"] == "ambiguous"
        assert len(result["matches"]) == 2
        # Never auto-picked one.
        assert result["status"] != "ready"


# ── mark_class_attendance: re-marking updates cleanly, never duplicates ──
# Explicit test for the user's requirement: repeated AI attendance marking
# for the same class/date must upsert through the same path the manual UI
# uses, not create duplicate rows or fail silently.


async def test_mark_attendance_via_ai_updates_existing_row_not_duplicate(
    client, admin_headers, teacher_headers, ai_enabled, monkeypatch
):
    manual = await client.post(
        "/api/attendance/mark",
        headers=teacher_headers,
        json={
            "class_id": 1, "section_id": 1, "date": "2026-09-01",
            "entries": [{"student_id": 1, "status": "present"}],
        },
    )
    assert manual.status_code == 201

    scripted = ScriptedAssistant(
        _tool_use(
            "t1", "mark_class_attendance",
            {"date": "2026-09-01", "absent_student_names": ["Sam Student"]},
        )
    )
    monkeypatch.setattr("app.services.ai.assistant.run_messages", scripted)

    chat = await client.post(
        "/api/ai/assistant/chat",
        headers=teacher_headers,
        json={"transcript": [{"role": "user", "text": "mark Sam Student absent today"}]},
    )
    assert chat.status_code == 200
    pending = chat.json()["pending_action"]
    assert pending is not None
    # Full resulting roster, not just the exceptions.
    assert any(row["status"] == "present" for row in pending["preview"]["roster"])
    assert any(row["status"] == "absent" for row in pending["preview"]["roster"])

    confirm = await client.post(
        "/api/ai/assistant/confirm", headers=teacher_headers, json={"action_id": pending["action_id"]}
    )
    assert confirm.status_code == 200

    from app.database import async_session_factory
    from app.models.attendance import Attendance

    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(Attendance).where(
                    and_(Attendance.student_id == 1, Attendance.date == date(2026, 9, 1))
                )
            )
        ).scalars().all()
    assert len(rows) == 1, "re-marking the same student/date/period must update, never duplicate"
    assert rows[0].status.value == "absent"

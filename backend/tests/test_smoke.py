"""Smoke tests covering auth, RBAC, public site, and the core flows."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


# ── Auth & RBAC ──────────────────────────────────────────────────────


async def test_me_requires_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_dev_token_resolves(client, admin_headers):
    response = await client.get("/api/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "super_admin"


async def test_unknown_dev_role_rejected(client):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer dev:hacker"})
    assert response.status_code == 401


async def test_teacher_cannot_manage_users(client, teacher_headers):
    response = await client.get("/api/users/", headers=teacher_headers)
    assert response.status_code == 403


async def test_student_cannot_see_defaulters(client, student_headers):
    response = await client.get("/api/fees/defaulters", headers=student_headers)
    assert response.status_code == 403


# ── Public website endpoints ─────────────────────────────────────────


async def test_public_reads(client):
    for path in ("/api/public/notices", "/api/public/faculty", "/api/public/school"):
        response = await client.get(path)
        assert response.status_code == 200, path


async def test_public_admission_enquiry(client, admin_headers):
    response = await client.post(
        "/api/admissions/enquiry",
        json={
            "child_name": "New Kid",
            "class_applying": "Class 1",
            "parent_name": "New Parent",
            "phone": "9111111111",
        },
    )
    assert response.status_code == 201
    listing = await client.get("/api/admissions/", headers=admin_headers)
    assert any(e["child_name"] == "New Kid" for e in listing.json())


async def test_public_contact_form(client, admin_headers):
    response = await client.post(
        "/api/public/contact",
        json={"name": "Visitor", "message": "What are the timings?"},
    )
    assert response.status_code == 201
    inbox = await client.get("/api/contact-messages/", headers=admin_headers)
    assert any(m["name"] == "Visitor" for m in inbox.json())


# ── Fees flow ────────────────────────────────────────────────────────


async def test_fee_flow(client, admin_headers, student_headers):
    structure = await client.post(
        "/api/fees/structures",
        headers=admin_headers,
        json={
            "class_id": 1,
            "academic_year_id": 1,
            "fee_head": "Tuition",
            "amount": 1000,
            "due_date": "2026-05-01",
            "term": "Term 1",
        },
    )
    assert structure.status_code == 201
    structure_id = structure.json()["id"]

    payment = await client.post(
        "/api/fees/pay",
        headers=admin_headers,
        json={
            "student_id": 1,
            "fee_structure_id": structure_id,
            "amount_paid": 400,
            "payment_mode": "cash",
        },
    )
    assert payment.status_code == 201
    txn_id = payment.json()["id"]
    assert payment.json()["receipt_number"].startswith("RCT-")

    receipt = await client.get(f"/api/fees/receipts/{txn_id}/html", headers=admin_headers)
    assert receipt.status_code == 200
    assert "FEE RECEIPT" in receipt.text

    # Student can open their own receipt, not blocked
    own = await client.get(f"/api/fees/receipts/{txn_id}/html", headers=student_headers)
    assert own.status_code == 200

    defaulters = await client.get("/api/fees/defaulters", headers=admin_headers)
    balances = [d["balance"] for d in defaulters.json() if d["fee_head"] == "Tuition"]
    assert 600.0 in balances

    my = await client.get("/api/fees/my", headers=student_headers)
    assert my.status_code == 200
    assert my.json()["items"][0]["paid"] == 400.0

    # Online payments cleanly unavailable without keys
    order = await client.post(
        "/api/fees/razorpay/order", headers=student_headers, json={"fee_structure_id": structure_id}
    )
    assert order.status_code == 503


# ── Exams flow incl. FR-16 ──────────────────────────────────────────


async def test_exam_flow_and_result_visibility(client, admin_headers, teacher_headers, student_headers):
    exam = await client.post(
        "/api/exams/",
        headers=admin_headers,
        json={
            "name": "Unit Test 1",
            "academic_year_id": 1,
            "class_id": 1,
            "exam_type": "Unit Test",
            "start_date": "2026-07-01",
            "end_date": "2026-07-05",
            "subjects": [{"subject_id": 1, "max_marks": 100, "passing_marks": 33}],
        },
    )
    assert exam.status_code in (200, 201)
    exam_id = exam.json()["id"]

    detail = await client.get(f"/api/exams/{exam_id}", headers=admin_headers)
    exam_subject_id = detail.json()["subjects"][0]["id"]

    marks = await client.post(
        "/api/exams/marks",
        headers=teacher_headers,
        json={"exam_subject_id": exam_subject_id, "entries": [{"student_id": 1, "marks_obtained": 88}]},
    )
    assert marks.status_code in (200, 201)

    # FR-16: hidden before publish
    card = await client.get(f"/api/exams/{exam_id}/report-card/1", headers=student_headers)
    assert card.status_code == 403

    await client.post(f"/api/exams/{exam_id}/lock", headers=admin_headers)
    published = await client.post(f"/api/exams/{exam_id}/publish", headers=admin_headers)
    assert published.status_code == 200

    card = await client.get(f"/api/exams/{exam_id}/report-card/1", headers=student_headers)
    assert card.status_code == 200
    assert card.json()["subjects"][0]["marks_obtained"] == 88.0
    assert card.json()["subjects"][0]["grade"] == "A"

    # Cannot read another student's card
    other = await client.get(f"/api/exams/{exam_id}/report-card/999", headers=student_headers)
    assert other.status_code == 403


# ── Attendance + absent automation logging ──────────────────────────


async def test_attendance_and_skipped_alert(client, admin_headers, teacher_headers, student_headers):
    # enable the automation so the alert path runs (logged as SKIPPED)
    await client.put(
        "/api/settings/automation", headers=admin_headers, json={"absent_alerts": True}
    )
    marked = await client.post(
        "/api/attendance/mark",
        headers=teacher_headers,
        json={
            "class_id": 1,
            "section_id": 1,
            "date": "2026-07-06",
            "entries": [{"student_id": 1, "status": "absent"}],
        },
    )
    assert marked.status_code == 201

    my = await client.get("/api/attendance/my", headers=student_headers)
    assert my.status_code == 200
    assert my.json()["absent"] >= 1

    log = await client.get("/api/communication/?delivery_status=skipped", headers=admin_headers)
    assert any("ABSENT" in (m["content_summary"] or "") for m in log.json())


# ── Promotion & exports ──────────────────────────────────────────────


async def test_csv_exports(client, admin_headers):
    for path in (
        "/api/students/export.csv",
        "/api/fees/transactions/export.csv",
        "/api/fees/defaulters/export.csv",
        "/api/attendance/export.csv",
    ):
        response = await client.get(path, headers=admin_headers)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/csv")


async def test_promote_validates_section(client, admin_headers):
    response = await client.post(
        "/api/students/promote",
        headers=admin_headers,
        json={"from_class_id": 1, "to_class_id": 2, "to_section_id": 1},
    )
    # class 2 doesn't exist / section 1 belongs to class 1 → validation error
    assert response.status_code == 400

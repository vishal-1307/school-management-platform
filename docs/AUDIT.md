# Platform Audit — SRS vs. Implementation

Audit date: 2026-07-07. Every claim below was verified against the code (file references included).
Status legend: ✅ Built · 🟡 Partial · ❌ Missing · 🔴 Built but broken / faked

## 1. Deployment & infrastructure

| Item | Status | Detail |
|---|---|---|
| Backend on Render | 🔴 Never deployed | No `render.yaml`/Procfile/start command existed. Three independent crash causes below. |
| DB schema on Postgres | 🔴 Deploy-blocker | `app/main.py` lifespan runs `create_all()` only for SQLite; `alembic/versions/` was empty → on Neon, zero tables exist and every endpoint 500s. |
| Neon URL handling | 🔴 Deploy-blocker | Neon URLs carry `?sslmode=require&channel_binding=require`; asyncpg rejects these params at connect. The scheme rewrite in `config.py` didn't strip them. |
| `CORS_ORIGINS` env parsing | 🔴 Deploy-blocker | pydantic-settings requires JSON for `List[str]`; a plain URL string crashes `Settings()` at import, before the port binds. |
| `setuptools`/razorpay | 🔴 Deploy-blocker | `requirements.txt` had unpinned `setuptools`; setuptools ≥81 removed `pkg_resources`, which `razorpay==1.4.2` imports → `ModuleNotFoundError` at boot (reproduced locally with setuptools 83). |
| Frontend on Vercel | ✅ (static) | Live, but static output + no adapter → cannot host auth-protected portals as-is. |
| Frontend→backend connection | ❌ | Zero `fetch`/API URL/env references in the entire frontend. |
| Tests / CI | ❌ | None anywhere. |

## 2. Backend vs SRS

| SRS area | Status | Detail |
|---|---|---|
| Auth (Clerk JWT) — §5, FR-1..3 | 🔴 | `middleware/auth.py` decodes JWTs with the *secret key*; `clerk_jwks_url` never used → real Clerk RS256 tokens can never verify. No Clerk user provisioning (seed uses fake `clerk_id`s). Logout is a no-op stub. |
| Role-based access — FR-2 | 🟡 | `require_role()` exists and is applied consistently, but unusable until token verification works. |
| Students CRUD/bulk import/TC — §6.2 | ✅ | Real logic. Missing: promote-class action, bonafide wiring. |
| Staff CRUD + assignments — §6.3 | ✅ | Missing: login credential creation (Clerk provisioning). |
| Student attendance — §6.6 | ✅ | Mark/list/override. Missing: staff-attendance endpoints (model exists, no routes), absent→WhatsApp alert (FR-9). |
| Fees — §6.5 | 🟡 | Structures, offline pay, defaulters, signature-verified webhook exist. Missing: online Pay-Now order+verify flow, receipts, exports, reminders. Bug: async `create_order` calls sync SDK (blocks event loop). |
| Exams/results — §6.7 | ✅ | CRUD, bulk marks + auto-grading, lock/publish, report card (HTML). Missing: results→WhatsApp, print polish. |
| Homework — §6.10/7.4 | ✅ | Missing: Cloudinary upload-signature endpoint for attachments. |
| Timetable — §6.8 | ✅ | Missing: double-booking conflict warning (FR-19). |
| Notices — §6.9 | 🟡 | CRUD only. "Channels" (website/WhatsApp) stored as JSON but nothing ever dispatches — faked in effect. No scheduled publishing. |
| Admissions pipeline — §6.4 | ✅ | Full status pipeline. |
| CMS — §6.11 | ✅ | Gallery/achievements/news CRUD; reads public. |
| Reports — §6.12 | ✅ | 3 report endpoints. Missing: exam summary, exports. |
| Communication log — §6.13 | 🟡 | Model + logging exist; no list endpoint. |
| User & role management — §6.15 | ❌ | No endpoints; no AuditLog model/trail. |
| School settings — §6.16 | ✅ | Complete. |
| Teacher leave — §7.8 | ❌ | No model, endpoints, or approval screen. |
| Automation settings — §6.14 | ❌ | Nothing. |
| Contact form intake — §4.2.11 | ❌ | No model/endpoint. |
| Public read APIs (website content) | ❌ | Notices/staff GETs are auth-only; public site has nothing to call. |

## 3. Frontend vs SRS

| SRS area | Status | Detail |
|---|---|---|
| Public pages ×11 + login gateway | ✅ (static) | Well-built and responsive, but 100% hardcoded content — CMS edits would never appear, defeating §2.1's "enter once, shows everywhere". |
| Admission form — FR-23 | 🔴 Faked | `AdmissionForm.tsx` simulated the API call (`setTimeout` + `console.log`) and showed success. |
| Contact form | 🔴 Faked | No submit handler at all. |
| Login gateway — §4.2.12 | 🔴 | All three portal cards `href="#"`. No Clerk packages installed. |
| Admin portal — §6 (16 modules) | ❌ | Zero pages exist. |
| Teacher portal — §7 (9 pages) | ❌ | Zero. |
| Student portal — §8 (8 pages) | ❌ | Zero. |
| Dead links | 🔴 | 8 disclosure document downloads, notice PDFs, academic-calendar PDF (missing file), footer social/privacy/terms — all `href="#"`. |

### Everything found faked or stubbed
1. Admission form — simulated submit (the known one).
2. Contact form — renders, submits nowhere.
3. Login gateway — dead links styled as portals.
4. JWT verification — verifies tokens real Clerk can never produce; logout returns fake success.
5. Notice channels — stored, never dispatched.
6. Seeded users — fake `clerk_id`s that can never match a real session.
7. Document download links across disclosure/notices/academics.

## 4. SRS critique — gaps for a 2026 school LMS

**Compliance:**
- **DPDP Act 2023** (children's data): needs verifiable parental consent, purpose limitation, retention/deletion policy. SRS only says "stored securely".
- **Photo consent** per student before public gallery publishing.
- Privacy Policy + Terms pages (also required for Razorpay onboarding).

**Functional gaps in the spec itself:**
- Leave approvals: teachers can apply (§7.8) but no admin approval module in §6.
- Fees: no partial payments, late fines, sibling/staff concessions, or receipt numbering series. "GST-ready" is misdirected — tuition is generally GST-exempt.
- WhatsApp-only comms with no failure fallback/retry (delivery failures are routine).
- No hall tickets/admit cards, co-scholastic grades (CBSE report cards need them), or attendance on report cards.
- No ID-card generation (near-universal school ask).
- Academic-year rollover: promotion specced, but fee carryover/section reassignment/archival aren't.
- No Hindi/English option for parent-facing content.
- No spam protection (captcha/rate limits) on public forms.
- No backup RPO/RTO, error tracking, or uptime monitoring requirements.
- No data-export/exit clause (school owns its data).

**Appropriately deferred by the SRS:** AI assistants, automated follow-ups, social auto-posting, transport/hostel/library/payroll.

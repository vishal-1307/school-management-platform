# School Website & Management Platform

Public website + role-based management portals (Admin / Teacher / Student, with parents using
the student login) for Knowledge Development Kindergarten Academy. Built per the SRS in this
repo (`srs_extracted.md`).

## Stack

| Layer | Tech |
|---|---|
| Public website + portals | Astro 5 + React 19 islands + Tailwind v4, Vercel (`@astrojs/vercel`) |
| API | FastAPI + SQLAlchemy 2 (async) + Alembic, Render |
| Database | Neon Postgres (prod) / SQLite (local dev) |
| Auth | Institutional login (ID + password, bcrypt + JWT) — no third-party provider |
| Payments | Razorpay (online fees) |
| Parent comms | WhatsApp Cloud API |
| Media | Cloudinary |

## Repo layout

```
frontend/   Astro site: public pages (static) + /admin /teacher /student portals (SSR)
backend/    FastAPI app: 20 routers under /api, models, services, Alembic migrations, tests
docs/       AUDIT.md, DEPLOYMENT.md, AUTH.md, SETUP_INTEGRATIONS.md
render.yaml Render blueprint for the backend
DEMO_CREDENTIALS.md  Demo account logins + how to wipe them before real data
```

## Local development

```bash
# backend (Python 3.12 — 3.14 cannot build the pinned deps)
cd backend
python -m venv venv && venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
python seed.py                              # demo data in SQLite (school.db)
python -m uvicorn app.main:app --port 8000 --reload

# frontend
cd frontend
npm install
PUBLIC_API_URL=http://localhost:8000 npm run dev
```

- Site: http://localhost:4321 · API docs: http://localhost:8000/docs
- Portals: http://localhost:4321/login — see `DEMO_CREDENTIALS.md` for accounts (`admin` /
  `Admin@2026`, `EMP-001` / `Teach@2026`, `ADM-00001` / `Study@2026`)
- Tests: `cd backend && venv/Scripts/python -m pytest`

Or just run `run_preview.bat` on Windows.

## Deployment

See **docs/DEPLOYMENT.md** (Neon → Render blueprint → Vercel env vars), **docs/AUTH.md** for how
login works, and **docs/SETUP_INTEGRATIONS.md** for Razorpay/WhatsApp/Cloudinary.

## Feature map (vs SRS)

- **Public site**: 11 pages + login gateway; notices/gallery/faculty/achievements load live from
  the CMS with hardcoded fallback; admission-enquiry and contact forms post to the backend
  (rate-limited).
- **Admin portal**: dashboard, students (CRUD, CSV import/export, TC/bonafide, class promotion,
  login creation), staff (+ subject assignments, login creation), admissions pipeline, fees
  (structures, payments, receipts, defaulters, reminders), attendance (students + staff,
  overrides), exams (marks, lock/publish, report cards, CSV), timetable builder
  (conflict-checked), notices (channels, scheduling, WhatsApp broadcast), homework oversight,
  website CMS, enquiries inbox, reports, communication log, leave approvals, users & roles
  (+ audit trail), school settings (+ automation toggles).
- **Teacher portal**: dashboard, personal timetable, attendance marking (scoped to assigned
  classes), homework + submission review (own assignments only), marks entry (own subjects only,
  frozen when locked), student roster (own classes only), notices, leave application, profile +
  password change.
- **Student portal** (shared with parents): dashboard, attendance history + %, homework +
  submission, published results + printable report card, timetable, class notices, fee status +
  Razorpay Pay Now + receipts, profile + password change.
- **Automations** (toggleable, logged as SKIPPED until WhatsApp is configured): absence alerts,
  notice broadcasts, fee reminders, results notifications.

## Security

Every teacher-facing endpoint is scoped to that teacher's actual class/subject assignments (not
just their role); public forms are rate-limited and length-capped; login is rate-limited and
timing-safe against user enumeration; sessions are revocable (password change/reset/deactivation
kill outstanding tokens instantly). See `docs/AUDIT.md` for the full security review this was
built against.

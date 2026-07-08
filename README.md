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
| Auth | Clerk (RS256 session tokens, role-based) with a demo `DEV_AUTH` fallback |
| Payments | Razorpay (online fees) |
| Parent comms | WhatsApp Cloud API |
| Media | Cloudinary |

## Repo layout

```
frontend/   Astro site: public pages (static) + /admin /teacher /student portals (SSR)
backend/    FastAPI app: 20 routers under /api, models, services, Alembic migrations, tests
docs/       AUDIT.md, DEPLOYMENT.md, SETUP_CLERK.md, SETUP_INTEGRATIONS.md
render.yaml Render blueprint for the backend
```

## Local development

```bash
# backend (Python 3.12 — 3.14 cannot build the pinned deps)
cd backend
python -m venv venv && venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
python seed.py                              # demo data in SQLite (school.db)
DEV_AUTH=true python -m uvicorn app.main:app --port 8000 --reload

# frontend
cd frontend
npm install
PUBLIC_DEV_AUTH=true PUBLIC_API_URL=http://localhost:8000 npm run dev
```

- Site: http://localhost:4321 · API docs: http://localhost:8000/docs
- Portals: http://localhost:4321/sign-in → pick a role (demo mode)
- Tests: `cd backend && venv/Scripts/python -m pytest`

Or just run `run_preview.bat` on Windows.

## Deployment

See **docs/DEPLOYMENT.md** (Neon → Render blueprint → Vercel env vars), then
**docs/SETUP_CLERK.md** for real logins and **docs/SETUP_INTEGRATIONS.md** for
Razorpay/WhatsApp/Cloudinary.

⚠️ `DEV_AUTH=true` lets anyone act as any role — demo only. Remove it the moment Clerk keys are
configured and before any real data is entered.

## Feature map (vs SRS)

- **Public site**: 11 pages + login gateway; notices/gallery/faculty/achievements load live from
  the CMS with hardcoded fallback; admission-enquiry and contact forms post to the backend.
- **Admin portal**: dashboard, students (CRUD, CSV import/export, TC/bonafide, class promotion),
  staff (+ subject assignments, login provisioning), admissions pipeline, fees (structures,
  payments, receipts, defaulters, reminders), attendance (students + staff, overrides), exams
  (marks, lock/publish, report cards, CSV), timetable builder (conflict-checked), notices
  (channels, scheduling, WhatsApp broadcast), homework oversight, website CMS, enquiries inbox,
  reports, communication log, leave approvals, users & roles (+ audit trail), school settings
  (+ automation toggles).
- **Teacher portal**: dashboard, personal timetable, attendance marking, homework + submission
  review, marks entry (scoped to own subjects, frozen when locked), student roster, notices,
  leave application, profile.
- **Student portal** (shared with parents): dashboard, attendance history + %, homework +
  submission, published results + printable report card, timetable, class notices, fee status +
  Razorpay Pay Now + receipts, profile.
- **Automations** (toggleable, logged as SKIPPED until WhatsApp is configured): absence alerts,
  notice broadcasts, fee reminders, results notifications.

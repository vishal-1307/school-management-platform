# Demo Login Credentials

⚠️ **This is demo data for evaluating the platform — not real school data.** The
passwords below are intentionally simple and are printed here in plain text.
**Wipe this data (see below) before entering any real student, staff, or fee
information.**

These accounts (and a full walkthrough dataset — attendance history, homework,
exam results, fee records, notices, a timetable, admission enquiries, and
contact messages) are created automatically the first time the backend boots
with `SEED_ON_START=true`. Every login uses the institutional ID + password
scheme — no third-party sign-up, no email required.

## Accounts

| Role | Login ID | Password | Notes |
|---|---|---|---|
| Super Admin | `admin` | `Admin@2026` | Full access to every module |
| Teacher | `EMP-001` | `Teach@2026` | Sunita Kaul — Mathematics, Class 3 & 4 |
| Teacher | `EMP-002` | `Teach@2026` | Ramesh Joshi — Science, Class 3 & 4 |
| Teacher | `EMP-003` | `Teach@2026` | Priya Sen — English/Hindi, Class 3 & 4 |
| Student | `ADM-00001` … `ADM-00010` | `Study@2026` | 4 in Class 3-A, 3 in Class 3-B, 3 in Class 4-A |

**Parents:** there is no separate parent login — parents sign in with their
child's student ID and password (e.g. `ADM-00001` / `Study@2026`) exactly as a
student would.

## What's in the walkthrough data

- **Attendance** — the last 10 school days for all 10 students, a realistic
  present/absent/late mix (one student, `ADM-00003`, is chronically absent —
  useful for testing the absence-alert automation).
- **Exams** — a *Half-Yearly Exam* with marks in Math + English, locked and
  **published** (visible to students), and a *Unit Test 2* with marks entered
  but **not published** (proves results stay hidden until the admin unlocks
  them).
- **Homework** — two assignments (Math, English) with submissions in every
  state: reviewed, submitted-pending-review, and not yet submitted.
- **Fees** — Tuition + Exam Fee for Class 3: one student fully paid, one
  partially paid, one with zero payments (the clearest defaulter), the rest
  fully paid tuition but not the exam fee.
- **Notices** — one for everyone, one targeted at Class 3 only, one staff-only.
- **Timetable** — a full Monday–Saturday schedule for Class 3-A.
- **Admissions** — three enquiries in different pipeline stages (New,
  Contacted, Admitted).
- **Contact messages** — two website contact-form submissions (one read, one
  unread).

## Wiping the demo data before real data goes in

Run this **from your own machine**, pointed at the production database — it
refuses to run against a local SQLite database, and requires typing the
database hostname to confirm (a plain `--yes` flag isn't enough on its own):

```bash
cd backend
# Put the real (production) Neon connection string in backend/.env for this
# one-time run — do NOT commit it.
echo 'DATABASE_URL=<paste the production Neon URL here>' >> .env

python -m app.scripts.reset_demo --yes
# It will ask you to type the database's hostname to confirm, then prompt
# for a new admin password (not printed or stored anywhere but the DB).
```

This deletes every data row (students, staff, attendance, fees, exams,
homework, notices, timetable, enquiries, everything) but keeps the database
schema intact, then re-creates only the school profile, current academic
year, standard classes/subjects, and a single `admin` login with the password
you just chose. No demo teachers/students/attendance are recreated.

After wiping, also set `SEED_ON_START=false` on Render (Environment tab) so a
future restart doesn't reseed the demo dataset.

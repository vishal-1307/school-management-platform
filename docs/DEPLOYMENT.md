# Deployment Guide

Two services: FastAPI backend on **Render** (+ **Neon** Postgres) and the Astro frontend on **Vercel**.

## Why previous deploys failed (fixed now)

1. **No tables on Postgres** — tables were only auto-created for SQLite. Fixed: a committed Alembic migration runs via `alembic upgrade head` in the Render start command.
2. **Neon URL params** — `?sslmode=require&channel_binding=require` crash asyncpg. Fixed: params are stripped automatically and SSL is applied via `connect_args`.
3. **`CORS_ORIGINS` format** — a plain string crashed settings at import (JSON was required). Fixed: JSON *or* comma-separated now both work.
4. **`setuptools` unpinned** — setuptools ≥81 removed `pkg_resources`, which the razorpay SDK imports, crashing at boot. Fixed: pinned `setuptools<81`.

## 1. Neon (database)

1. Create a project at neon.tech (region: ap-southeast-1 / Singapore is closest to India).
2. Copy the **pooled** connection string (the one with `-pooler` in the host). Paste it as-is — no editing needed.

## 2. Render (backend)

1. Render dashboard → **New → Blueprint** → select this GitHub repo. It reads `render.yaml` automatically.
2. When prompted, paste the Neon pooled URL into `DATABASE_URL`.
3. Deploy. First boot runs migrations and the bootstrap seed (school profile, classes Nursery→Class 12, subjects, a pending super-admin user).
4. Verify: `https://<service>.onrender.com/health` → `{"status":"ok","database":"ok"}`. If `database` shows an error, the message tells you exactly what's wrong.
5. Note the service URL — the frontend needs it as `PUBLIC_API_URL`.

Defaults set by the blueprint: `SEED_ON_START=true` (idempotent, safe to keep), `DEV_AUTH=true` (**demo only** — anyone can act as any role; delete this env var the moment Clerk keys are added).

Free-tier note: the service spins down after idle and takes ~50s to wake. The public website is built to render instantly regardless (static content with background refresh).

## 3. Vercel (frontend)

Project already exists (school-management-platform-five.vercel.app). Add env vars in Project → Settings → Environment Variables:

| Var | Value |
|---|---|
| `PUBLIC_API_URL` | `https://<service>.onrender.com` |
| `PUBLIC_DEV_AUTH` | `true` (demo only — remove with Clerk setup) |
| `PUBLIC_CLERK_PUBLISHABLE_KEY` | (after Clerk setup) |
| `CLERK_SECRET_KEY` | (after Clerk setup) |

Then redeploy.

## 4. Later: real keys

- **Clerk** → see `docs/SETUP_CLERK.md`
- **Razorpay / WhatsApp / Cloudinary** → see `docs/SETUP_INTEGRATIONS.md`

Each integration is optional-at-boot: the app runs fine without keys and degrades gracefully (online payments return 503 with a clear message, WhatsApp sends are logged as SKIPPED, uploads are disabled).

## Local development

```bat
run_preview.bat
```
or manually:
```bash
cd backend && python seed.py && python -m uvicorn app.main:app --port 8000 --reload
cd frontend && npm install && npm run dev
```
Backend docs: http://127.0.0.1:8000/docs · Site: http://localhost:4321
Local dev uses SQLite (`school.db`) — no env vars needed. Python 3.12 required (3.14 cannot build asyncpg/pydantic wheels).

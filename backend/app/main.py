"""FastAPI main application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from app.config import settings
from app.routers import (
    auth_router,
    students_router,
    staff_router,
    attendance_router,
    fees_router,
    exams_router,
    homework_router,
    timetable_router,
    notices_router,
    admissions_router,
    cms_router,
    reports_router,
    settings_router,
    users_router,
    public_router,
    contact_router,
    uploads_router,
    communication_router,
    leaves_router,
    ai_router,
)

from contextlib import asynccontextmanager

from sqlalchemy import text

from app.database import Base, engine
import app.models  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    if settings.seed_on_start:
        from app.scripts.seed_prod import seed_production

        await seed_production()
    yield

app = FastAPI(
    title="Knowledge Development Kindergarten Academy API",
    description="School Website & Management Platform Backend API",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS configuration. Never falls back to "*" — an empty CORS_ORIGINS
# (misconfiguration) restricts to localhost dev origins rather than
# opening up to every origin while allow_credentials=True is set (that
# combination lets any website read authenticated responses).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Verify backend and database connection status.

    Failure detail is logged server-side only — the response never
    exposes driver/connection internals to an unauthenticated caller.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # pragma: no cover - depends on infra state
        logger.exception("Health check: database connection failed")
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
    }


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(students_router, prefix="/api")
app.include_router(staff_router, prefix="/api")
app.include_router(attendance_router, prefix="/api")
app.include_router(fees_router, prefix="/api")
app.include_router(exams_router, prefix="/api")
app.include_router(homework_router, prefix="/api")
app.include_router(timetable_router, prefix="/api")
app.include_router(notices_router, prefix="/api")
app.include_router(admissions_router, prefix="/api")
app.include_router(cms_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(contact_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(communication_router, prefix="/api")
app.include_router(leaves_router, prefix="/api")
app.include_router(ai_router, prefix="/api")

"""Routers package."""

from app.routers.auth import router as auth_router
from app.routers.students import router as students_router
from app.routers.staff import router as staff_router
from app.routers.attendance import router as attendance_router
from app.routers.fees import router as fees_router
from app.routers.exams import router as exams_router
from app.routers.homework import router as homework_router
from app.routers.timetable import router as timetable_router
from app.routers.notices import router as notices_router
from app.routers.admissions import router as admissions_router
from app.routers.cms import router as cms_router
from app.routers.reports import router as reports_router
from app.routers.settings import router as settings_router
from app.routers.users import router as users_router
from app.routers.public import router as public_router
from app.routers.contact import router as contact_router
from app.routers.uploads import router as uploads_router
from app.routers.communication import router as communication_router
from app.routers.leaves import router as leaves_router

__all__ = [
    "leaves_router",
    "users_router",
    "public_router",
    "contact_router",
    "uploads_router",
    "communication_router",
    "auth_router",
    "students_router",
    "staff_router",
    "attendance_router",
    "fees_router",
    "exams_router",
    "homework_router",
    "timetable_router",
    "notices_router",
    "admissions_router",
    "cms_router",
    "reports_router",
    "settings_router",
]

"""Reporting API router."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.schemas.dashboard import AdminDashboardResponse
from app.services.reports import (
    attendance_trends as get_attendance_trends,
    fee_collection_summary as get_fee_collection_summary,
    admission_funnel as get_admission_funnel,
    admin_dashboard_summary as get_admin_dashboard_summary,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


@router.get("/dashboard-summary", response_model=AdminDashboardResponse)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> AdminDashboardResponse:
    """Everything the admin dashboard needs, in one request."""
    return await get_admin_dashboard_summary(db)


@router.get("/attendance-trends")
async def attendance_trends(
    class_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Get daily attendance counts and trends."""
    data = await get_attendance_trends(db, class_id=class_id, start_date=start_date, end_date=end_date)
    return {"data": data}


@router.get("/fee-collection-summary")
async def fee_collection_summary(
    academic_year_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Get aggregate fee collection metrics and breakdowns."""
    data = await get_fee_collection_summary(db, academic_year_id=academic_year_id)
    return data


@router.get("/admission-funnel")
async def admission_funnel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Get admission funnel pipeline analysis and conversion rate."""
    data = await get_admission_funnel(db)
    return data

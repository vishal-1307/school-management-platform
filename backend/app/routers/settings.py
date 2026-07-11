"""Settings API router for school profile, academic year, class, section, subject setup."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.school import School
from app.models.academic import AcademicYear, Class, Section, Subject
from app.models.user import User, UserRole
from app.schemas.settings import (
    SchoolBase,
    SchoolResponse,
    AcademicYearCreate,
    AcademicYearResponse,
    ClassCreate,
    ClassResponse,
    SectionCreate,
    SectionResponse,
    SubjectCreate,
    SubjectResponse,
)

router = APIRouter(prefix="/settings", tags=["Settings"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


# School Profile Endpoints
@router.get("/school", response_model=SchoolResponse)
async def get_school_profile(db: AsyncSession = Depends(get_db)):
    """Get the school profile details. Returns default if none exists."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    if not school:
        # Create a default school profile if none exists
        school = School(name="Knowledge Development Kindergarten Academy")
        db.add(school)
        await db.flush()
        await db.refresh(school)
    return school


@router.put("/school", response_model=SchoolResponse)
async def update_school_profile(
    payload: SchoolBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Update the school profile details."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    if not school:
        school = School(name=payload.name)
        db.add(school)
    
    school.name = payload.name
    school.logo_url = payload.logo_url
    school.address = payload.address
    school.affiliation_number = payload.affiliation_number
    school.contact_email = payload.contact_email
    school.contact_phone = payload.contact_phone
    school.settings = payload.settings or {}
    
    await db.flush()
    await db.refresh(school)
    return school


# Automation toggles (SRS 6.14) — stored in School.settings JSON
AUTOMATION_DEFAULTS = {
    "absent_alerts": False,
    "fee_reminders": False,
    "notice_broadcast": False,
    "results_notification": False,
}


@router.get("/automation")
async def get_automation_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> dict:
    """Current automation on/off switches."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    stored = (school.settings or {}).get("automation", {}) if school else {}
    return {**AUTOMATION_DEFAULTS, **stored}


@router.put("/automation")
async def update_automation_settings(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> dict:
    """Toggle automations; unknown keys are ignored."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="School profile not set up yet")
    current = {**AUTOMATION_DEFAULTS, **(school.settings or {}).get("automation", {})}
    for key in AUTOMATION_DEFAULTS:
        if key in payload:
            current[key] = bool(payload[key])
    new_settings = dict(school.settings or {})
    new_settings["automation"] = current
    school.settings = new_settings
    await db.flush()
    return current


# Feature add-ons — stored in School.settings JSON, same pattern as automation.
FEATURE_DEFAULTS = {
    "ai_assistant_enabled": False,
}


@router.get("/features")
async def get_feature_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> dict:
    """Current paid add-on feature toggles."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    stored = (school.settings or {}).get("features", {}) if school else {}
    return {**FEATURE_DEFAULTS, **stored}


@router.put("/features")
async def update_feature_settings(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
) -> dict:
    """Toggle feature add-ons; unknown keys are ignored."""
    result = await db.execute(select(School))
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="School profile not set up yet")
    current = {**FEATURE_DEFAULTS, **(school.settings or {}).get("features", {})}
    for key in FEATURE_DEFAULTS:
        if key in payload:
            current[key] = bool(payload[key])
    new_settings = dict(school.settings or {})
    new_settings["features"] = current
    school.settings = new_settings
    await db.flush()
    return current


# Academic Years Endpoints
@router.get("/academic-years", response_model=list[AcademicYearResponse])
async def list_academic_years(db: AsyncSession = Depends(get_db)):
    """List all academic years."""
    result = await db.execute(select(AcademicYear).order_by(AcademicYear.start_date.desc()))
    return result.scalars().all()


@router.post("/academic-years", response_model=AcademicYearResponse, status_code=status.HTTP_201_CREATED)
async def create_academic_year(
    payload: AcademicYearCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new academic year."""
    if payload.is_current:
        # Set all others to False first
        await db.execute(update(AcademicYear).values(is_current=False))
        
    year = AcademicYear(
        label=payload.label,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
    )
    db.add(year)
    await db.flush()
    await db.refresh(year)
    return year


@router.put("/academic-years/{year_id}/current", response_model=AcademicYearResponse)
async def set_current_academic_year(
    year_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Set the specified academic year as the current one."""
    year = await db.get(AcademicYear, year_id)
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found")
        
    await db.execute(update(AcademicYear).values(is_current=False))
    year.is_current = True
    await db.flush()
    await db.refresh(year)
    return year


# Classes Endpoints
@router.get("/classes", response_model=list[ClassResponse])
async def list_classes(db: AsyncSession = Depends(get_db)):
    """List all classes."""
    result = await db.execute(select(Class).order_by(Class.numeric_order.asc()))
    return result.scalars().all()


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new class."""
    result = await db.execute(select(Class).where(Class.name == payload.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Class name already exists")
        
    new_class = Class(name=payload.name, numeric_order=payload.numeric_order)
    db.add(new_class)
    await db.flush()
    await db.refresh(new_class)
    return new_class


# Sections Endpoints
@router.get("/sections", response_model=list[SectionResponse])
async def list_sections(class_id: int | None = None, db: AsyncSession = Depends(get_db)):
    """List all sections, optionally filtered by class_id."""
    query = select(Section)
    if class_id:
        query = query.where(Section.class_id == class_id)
    query = query.order_by(Section.name.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new section within a class."""
    result = await db.execute(
        select(Section).where(Section.name == payload.name, Section.class_id == payload.class_id)
    )
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Section already exists in this class")
        
    section = Section(
        name=payload.name,
        class_id=payload.class_id,
        class_teacher_id=payload.class_teacher_id,
    )
    db.add(section)
    await db.flush()
    await db.refresh(section)
    return section


# Subjects Endpoints
@router.get("/subjects", response_model=list[SubjectResponse])
async def list_subjects(db: AsyncSession = Depends(get_db)):
    """List all subjects."""
    result = await db.execute(select(Subject).order_by(Subject.name.asc()))
    return result.scalars().all()


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new subject."""
    result = await db.execute(select(Subject).where(Subject.code == payload.code))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Subject code already exists")
        
    subject = Subject(name=payload.name, code=payload.code)
    db.add(subject)
    await db.flush()
    await db.refresh(subject)
    return subject

"""CMS API router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_role
from app.models.cms import GalleryAlbum, GalleryImage, Achievement, NewsEvent
from app.models.user import User, UserRole
from app.schemas.cms import (
    GalleryAlbumCreate,
    GalleryAlbumResponse,
    GalleryImageCreate,
    GalleryImageResponse,
    AchievementCreate,
    AchievementResponse,
    NewsEventCreate,
    NewsEventResponse,
)

router = APIRouter(prefix="/cms", tags=["CMS"])

ADMIN_ROLES = (UserRole.SUPER_ADMIN, UserRole.OFFICE_ADMIN)


# Gallery Album Endpoints
@router.get("/albums", response_model=list[GalleryAlbumResponse])
async def list_albums(db: AsyncSession = Depends(get_db)):
    """List all gallery albums."""
    result = await db.execute(select(GalleryAlbum).order_by(GalleryAlbum.created_at.desc()))
    return result.scalars().all()


@router.post("/albums", response_model=GalleryAlbumResponse, status_code=status.HTTP_201_CREATED)
async def create_album(
    payload: GalleryAlbumCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new gallery album."""
    album = GalleryAlbum(title=payload.title, description=payload.description)
    db.add(album)
    await db.flush()
    await db.refresh(album)
    return album


@router.get("/albums/{album_id}", response_model=GalleryAlbumResponse)
async def get_album(album_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific gallery album by ID."""
    album = await db.get(GalleryAlbum, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return album


@router.delete("/albums/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album(
    album_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Delete a gallery album."""
    album = await db.get(GalleryAlbum, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    await db.delete(album)
    await db.flush()
    return


@router.post("/albums/{album_id}/images", response_model=GalleryImageResponse, status_code=status.HTTP_201_CREATED)
async def add_image_to_album(
    album_id: int,
    payload: GalleryImageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Add a new image to an album."""
    album = await db.get(GalleryAlbum, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    
    image = GalleryImage(album_id=album_id, image_url=payload.image_url, caption=payload.caption)
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Delete an image."""
    image = await db.get(GalleryImage, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    await db.delete(image)
    await db.flush()
    return


# Achievements Endpoints
@router.get("/achievements", response_model=list[AchievementResponse])
async def list_achievements(db: AsyncSession = Depends(get_db)):
    """List all achievements."""
    result = await db.execute(select(Achievement).order_by(Achievement.date.desc()))
    return result.scalars().all()


@router.post("/achievements", response_model=AchievementResponse, status_code=status.HTTP_201_CREATED)
async def create_achievement(
    payload: AchievementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new achievement record."""
    achievement = Achievement(
        title=payload.title,
        description=payload.description,
        image_url=payload.image_url,
        date=payload.date,
        category=payload.category,
    )
    db.add(achievement)
    await db.flush()
    await db.refresh(achievement)
    return achievement


@router.delete("/achievements/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_achievement(
    achievement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Delete an achievement."""
    achievement = await db.get(Achievement, achievement_id)
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found")
    await db.delete(achievement)
    await db.flush()
    return


# News & Events Endpoints
@router.get("/news", response_model=list[NewsEventResponse])
async def list_news(is_published: bool = True, db: AsyncSession = Depends(get_db)):
    """List news and events."""
    query = select(NewsEvent)
    if is_published:
        query = query.where(NewsEvent.is_published == True)
    query = query.order_by(NewsEvent.event_date.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/news", response_model=NewsEventResponse, status_code=status.HTTP_201_CREATED)
async def create_news(
    payload: NewsEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Create a new news or event record."""
    news = NewsEvent(
        title=payload.title,
        description=payload.description,
        image_url=payload.image_url,
        event_date=payload.event_date,
        is_published=payload.is_published,
    )
    db.add(news)
    await db.flush()
    await db.refresh(news)
    return news


@router.put("/news/{news_id}", response_model=NewsEventResponse)
async def update_news(
    news_id: int,
    payload: NewsEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Update a news/event record."""
    news = await db.get(NewsEvent, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News record not found")
    
    news.title = payload.title
    news.description = payload.description
    news.image_url = payload.image_url
    news.event_date = payload.event_date
    news.is_published = payload.is_published
    
    await db.flush()
    await db.refresh(news)
    return news


@router.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Delete a news record."""
    news = await db.get(NewsEvent, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News record not found")
    await db.delete(news)
    await db.flush()
    return

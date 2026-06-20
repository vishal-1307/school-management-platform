"""CMS Pydantic schemas."""

from __future__ import annotations
import datetime
from pydantic import BaseModel, Field


class GalleryImageBase(BaseModel):
    image_url: str = Field(..., max_length=512)
    caption: str | None = Field(None, max_length=255)


class GalleryImageCreate(GalleryImageBase):
    album_id: int


class GalleryImageResponse(GalleryImageBase):
    id: int
    album_id: int

    class Config:
        from_attributes = True


class GalleryAlbumBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None


class GalleryAlbumCreate(GalleryAlbumBase):
    pass


class GalleryAlbumResponse(GalleryAlbumBase):
    id: int
    created_at: datetime.datetime
    images: list[GalleryImageResponse] = []

    class Config:
        from_attributes = True


class AchievementBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    image_url: str | None = Field(None, max_length=512)
    date: datetime.date | None = None
    category: str | None = Field(None, max_length=50, description="sports/academics/cultural")


class AchievementCreate(AchievementBase):
    pass


class AchievementResponse(AchievementBase):
    id: int

    class Config:
        from_attributes = True


class NewsEventBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    image_url: str | None = Field(None, max_length=512)
    event_date: datetime.date | None = None
    is_published: bool = False


class NewsEventCreate(NewsEventBase):
    pass


class NewsEventResponse(NewsEventBase):
    id: int

    class Config:
        from_attributes = True


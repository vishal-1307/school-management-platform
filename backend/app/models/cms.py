"""CMS models — GalleryAlbum, GalleryImage, Achievement, NewsEvent."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GalleryAlbum(Base):
    """Photo album for the school gallery."""

    __tablename__ = "gallery_albums"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    images: Mapped[list["GalleryImage"]] = relationship(
        back_populates="album", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<GalleryAlbum id={self.id} title={self.title!r}>"


class GalleryImage(Base):
    """Image within a gallery album."""

    __tablename__ = "gallery_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("gallery_albums.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255))

    album: Mapped["GalleryAlbum"] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<GalleryImage id={self.id} album={self.album_id}>"


class Achievement(Base):
    """School or student achievement / award."""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))
    date: Mapped[date | None] = mapped_column(Date)
    category: Mapped[str | None] = mapped_column(String(50), comment="sports/academics/cultural")

    def __repr__(self) -> str:
        return f"<Achievement id={self.id} title={self.title!r}>"


class NewsEvent(Base):
    """School news article or upcoming event."""

    __tablename__ = "news_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))
    event_date: Mapped[date | None] = mapped_column(Date)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    def __repr__(self) -> str:
        return f"<NewsEvent id={self.id} title={self.title!r}>"

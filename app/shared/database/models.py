from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class EventCache(Base):
    """Cache scraped event data with change detection"""

    __tablename__ = "events"

    id: Mapped[int] = Column(Integer, primary_key=True)
    source_url: Mapped[str] = Column(String(2048), unique=True, nullable=False)
    scraped_data: Mapped[dict[str, Any]] = Column(JSON, nullable=False)
    scraped_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    data_hash: Mapped[str] = Column(String(64), nullable=False)  # For change detection
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False,
    )

    # Relationship to submissions
    submissions: Mapped[list[Submission]] = relationship(
        "Submission", back_populates="event", cascade="all, delete-orphan",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_source_url", "source_url"),
        Index("idx_scraped_at", "scraped_at"),
        Index("idx_data_hash", "data_hash"),
    )

    def __repr__(self: EventCache) -> str:
        return f"<EventCache(id={self.id}, url='{self.source_url}')>"


class Submission(Base):
    """Track submission attempts to various services"""

    __tablename__ = "submissions"

    id: Mapped[int] = Column(Integer, primary_key=True)
    event_cache_id: Mapped[int] = Column(
        Integer, ForeignKey("events.id"), nullable=False,
    )
    service_name: Mapped[str] = Column(String(100), nullable=False)
    status: Mapped[str] = Column(
        String(20), nullable=False, default="pending",
    )  # pending, success, failed, retry
    submitted_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), nullable=False,
    )
    response_data: Mapped[dict[str, Any] | None] = Column(JSON, nullable=True)
    error_message: Mapped[str | None] = Column(Text, nullable=True)
    retry_count: Mapped[int] = Column(Integer, default=0, nullable=False)
    selection_criteria: Mapped[dict[str, Any] | None] = Column(JSON, nullable=True)
    batch_id: Mapped[str | None] = Column(
        String(36), nullable=True,
    )  # UUID for batching

    # Relationship to event
    event: Mapped[EventCache] = relationship("EventCache", back_populates="submissions")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_service_status", "service_name", "status"),
        Index("idx_submitted_at", "submitted_at"),
        Index("idx_batch_id", "batch_id"),
        Index("idx_event_service", "event_cache_id", "service_name"),
    )

    def __repr__(self: Submission) -> str:
        return f"<Submission(id={self.id}, service='{self.service_name}', status='{self.status}')>"

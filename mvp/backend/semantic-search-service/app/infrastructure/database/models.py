"""
SQLAlchemy models for application-specific data.
These models are separate from the Qdrant vector database.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    BigInteger,
    func,
    Index,
    UUID as SQLUUID,
    Text,
    CheckConstraint,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class UsageTracking(Base):
    """Track usage statistics for each content item."""

    __tablename__ = "usage_tracking"

    content_id = Column(SQLUUID(as_uuid=True), primary_key=True)
    usage_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    first_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship to usage events
    events = relationship(
        "UsageEvent", back_populates="tracking", cascade="all, delete-orphan"
    )

    def increment_usage(self, timestamp: Optional[datetime] = None):
        """Increment the usage count and update timestamps."""
        if self.usage_count is None:
            self.usage_count = 0
        self.usage_count += 1
        now = timestamp or datetime.utcnow()
        self.last_used = now
        if self.first_used is None:
            self.first_used = now


class UsageEvent(Base):
    """Track individual usage events for analytics."""

    __tablename__ = "usage_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    content_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("usage_tracking.content_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(255), nullable=True)
    event_type = Column(String(50), default="copy", nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    session_id = Column(String(255), nullable=True)
    ip_hash = Column(String(64), nullable=True)  # Store hashed IP for privacy
    user_agent = Column(String(500), nullable=True)

    # Relationship to tracking
    tracking = relationship("UsageTracking", back_populates="events")

    # Indexes for performance
    __table_args__ = (
        Index("idx_usage_events_content_id", "content_id"),
        Index("idx_usage_events_user_id", "user_id"),
        Index("idx_usage_events_timestamp", "timestamp"),
    )


class SearchEvent(Base):
    """Track search events for analytics and metrics.

    Holds no personally identifiable data. The columns query_text, user_id,
    session_id and ip_hash were dropped: query_text and ip_hash were written but
    never read by any query, and user_id/session_id are replaced by actor_hash.

    actor_hash is a keyed SHA-256 over the user or session id plus the UTC date,
    so it cannot be resolved back to a person and cannot be correlated across day
    boundaries. See SearchTrackingService._derive_actor_hash.
    """

    __tablename__ = "search_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_hash = Column(String(64), nullable=True)
    results_count = Column(Integer, default=0, nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_search_events_actor_hash", "actor_hash"),
        Index("idx_search_events_timestamp", "timestamp"),
    )


class ContentReport(Base):
    """Track user reports of inappropriate or problematic content."""

    __tablename__ = "content_reports"

    id = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    content_id = Column(SQLUUID(as_uuid=True), nullable=False)
    content_type = Column(String(50), nullable=False)
    reported_by_user_id = Column(String(255), nullable=True)
    reported_by_session_id = Column(String(255), nullable=True)
    reason = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), server_default="pending", nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Indexes and constraints
    __table_args__ = (
        Index("idx_content_reports_content_id", "content_id"),
        Index("idx_content_reports_status", "status"),
        Index("idx_content_reports_created", "created"),
        CheckConstraint(
            "(reported_by_user_id IS NOT NULL OR reported_by_session_id IS NOT NULL)",
            name="check_reporter_exists",
        ),
    )

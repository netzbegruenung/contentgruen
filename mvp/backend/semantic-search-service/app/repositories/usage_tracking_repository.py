"""
Repository for managing usage tracking data.
Handles all database operations for usage statistics.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
import asyncio

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import UsageTracking, UsageEvent

logger = logging.getLogger(__name__)


class UsageTrackingRepository:
    """Repository for usage tracking operations."""

    def __init__(self):
        self.db = get_app_database()

    def track_usage(
        self,
        content_id: uuid.UUID,
        user_id: Optional[str] = None,
        event_type: str = "copy",
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Track a usage event for a content item.

        Args:
            content_id: UUID of the content item
            user_id: Optional user identifier
            event_type: Type of usage event (default: "copy")
            session_id: Optional session identifier
            ip_address: Optional IP address (will be hashed)
            user_agent: Optional user agent string

        Returns:
            bool: True if tracking was successful
        """
        logger.info(
            f"Repository: Tracking usage for content {content_id}, user: {user_id}, event: {event_type}"
        )
        try:
            with self.db.get_session() as session:
                # Get or create usage tracking record
                tracking = (
                    session.query(UsageTracking)
                    .filter_by(content_id=content_id)
                    .first()
                )

                if not tracking:
                    tracking = UsageTracking(content_id=content_id, usage_count=0)
                    session.add(tracking)

                # Increment usage count
                tracking.increment_usage()

                # Hash IP address for privacy
                ip_hash = None
                if ip_address:
                    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()

                # Create usage event record
                event = UsageEvent(
                    content_id=content_id,
                    user_id=user_id,
                    event_type=event_type,
                    session_id=session_id,
                    ip_hash=ip_hash,
                    user_agent=user_agent[:500] if user_agent else None,  # Limit length
                )
                session.add(event)

                session.commit()
                logger.info(
                    f"Repository: Successfully tracked usage for content {content_id}, new count: {tracking.usage_count}"
                )
                return True

        except Exception as e:
            logger.error(
                f"Error tracking usage for content {content_id}: {e}", exc_info=True
            )
            return False

    def get_usage_count(self, content_id: uuid.UUID) -> int:
        """
        Get the usage count for a specific content item.

        Args:
            content_id: UUID of the content item

        Returns:
            int: Usage count (0 if not found)
        """
        with self.db.get_session() as session:
            tracking = (
                session.query(UsageTracking).filter_by(content_id=content_id).first()
            )
            return tracking.usage_count if tracking else 0

    def get_usage_counts_batch(self, content_ids: List[uuid.UUID]) -> Dict[str, int]:
        """
        Get usage counts for multiple content items.

        Args:
            content_ids: List of content UUIDs

        Returns:
            Dict mapping content_id (as string) to usage count
        """
        with self.db.get_session() as session:
            trackings = (
                session.query(UsageTracking)
                .filter(UsageTracking.content_id.in_(content_ids))
                .all()
            )

            result = {str(content_id): 0 for content_id in content_ids}
            for tracking in trackings:
                result[str(tracking.content_id)] = tracking.usage_count

            return result

    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific user's contributed content.

        Uses Qdrant as the source of truth for content ownership (original_author field),
        then gets usage counts from the usage_tracking table. This ensures statistics
        remain accurate even after old usage_events are cleaned up.

        Args:
            user_id: User identifier

        Returns:
            Dict containing user statistics
        """
        from repositories.aggregated.content_repository import ContentRepository
        from core.config import settings

        # Query Qdrant for all content created by this user
        content_repo = ContentRepository(settings)

        # Get all content by this author (using scroll/pagination)
        user_content = await content_repo.get_by_author(user_id, limit=10000, offset=0)

        if not user_content:
            return {
                "user_id": user_id,
                "unique_contents_contributed": 0,
                "total_usage_count": 0,
                "top_content": [],
            }

        # Extract content IDs
        content_ids = [content.id for content in user_content]

        # Get usage counts from usage_tracking table
        with self.db.get_session() as session:
            trackings = (
                session.query(UsageTracking)
                .filter(UsageTracking.content_id.in_(content_ids))
                .all()
            )

            # Build lookup map
            usage_map = {
                tracking.content_id: tracking.usage_count for tracking in trackings
            }

            # Calculate total usage
            total_usage = sum(usage_map.values())

            # Get top 5 content items by usage
            content_with_usage = [
                {
                    "content_id": str(content_id),
                    "usage_count": usage_map.get(content_id, 0),
                }
                for content_id in content_ids
            ]
            top_content = sorted(
                content_with_usage, key=lambda x: x["usage_count"], reverse=True
            )[:5]

            return {
                "user_id": user_id,
                "unique_contents_contributed": len(content_ids),
                "total_usage_count": total_usage,
                "top_content": top_content,
            }

    def get_trending_content(
        self, limit: int = 10, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get trending content based on recent usage.

        Args:
            limit: Maximum number of items to return
            days: Number of days to consider for trending

        Returns:
            List of trending content with usage stats
        """
        from datetime import timedelta

        with self.db.get_session() as session:
            since_date = datetime.utcnow() - timedelta(days=days)

            trending = (
                session.query(
                    UsageEvent.content_id,
                    func.count(UsageEvent.id).label("recent_uses"),
                    UsageTracking.usage_count.label("total_uses"),
                )
                .select_from(UsageEvent)
                .join(UsageTracking, UsageEvent.content_id == UsageTracking.content_id)
                .filter(
                    UsageEvent.timestamp >= since_date, UsageEvent.event_type == "copy"
                )
                .group_by(UsageEvent.content_id, UsageTracking.usage_count)
                .order_by(desc("recent_uses"))
                .limit(limit)
                .all()
            )

            return [
                {
                    "content_id": str(content_id),
                    "recent_uses": recent,
                    "total_uses": total,
                }
                for content_id, recent, total in trending
            ]

    def initialize_usage_data(self, content_id: uuid.UUID, initial_count: int = 0):
        """
        Initialize usage tracking for a content item with a specific count.
        Used for seeding data.

        Args:
            content_id: UUID of the content item
            initial_count: Initial usage count
        """
        with self.db.get_session() as session:
            tracking = (
                session.query(UsageTracking).filter_by(content_id=content_id).first()
            )

            if not tracking:
                tracking = UsageTracking(
                    content_id=content_id,
                    usage_count=initial_count,
                    first_used=datetime.utcnow() if initial_count > 0 else None,
                    last_used=datetime.utcnow() if initial_count > 0 else None,
                )
                session.add(tracking)
                session.commit()

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Clean up old usage events from the database.

        Only deletes from usage_events table - usage_tracking aggregate counters
        are preserved forever. This maintains accurate total usage counts while
        removing detailed event history for privacy compliance.

        Args:
            days_to_keep: Number of days of event data to retain (default: 90)

        Returns:
            int: Number of event records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        logger.info(
            f"Cleaning up usage events older than {days_to_keep} days (before {cutoff_date})"
        )

        try:
            with self.db.get_session() as session:
                # Delete old events
                deleted_count = (
                    session.query(UsageEvent)
                    .filter(UsageEvent.timestamp < cutoff_date)
                    .delete(synchronize_session=False)
                )

                session.commit()

                logger.info(f"Deleted {deleted_count} old usage event records")
                return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup of old events: {e}", exc_info=True)
            raise


# Global repository instance
_usage_repository: Optional[UsageTrackingRepository] = None


def get_usage_repository() -> UsageTrackingRepository:
    """Get or create the global usage repository instance."""
    global _usage_repository
    if _usage_repository is None:
        _usage_repository = UsageTrackingRepository()
    return _usage_repository

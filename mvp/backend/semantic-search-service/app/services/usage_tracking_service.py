"""
Service layer for usage tracking functionality.
Provides business logic for tracking and retrieving usage statistics.
"""

import logging
from typing import Optional, List, Dict, Any
import uuid
import hashlib

from repositories.usage_tracking_repository import get_usage_repository
from services.cache.cache_manager import get_trending_cache

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Service for managing usage tracking."""

    def __init__(self):
        self.repository = get_usage_repository()
        self.cache = get_trending_cache()

    def _validate_content_id(self, content_id: Optional[str]) -> bool:
        """
        Validate that a content ID is a valid UUID string.

        Args:
            content_id: The content ID to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not content_id:
            return False
        try:
            uuid.UUID(content_id)
            return True
        except (ValueError, AttributeError):
            return False

    def track_content_usage(
        self,
        content_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Track that a content item was used (copied).

        Args:
            content_id: String UUID of the content item
            user_id: Optional user identifier
            session_id: Optional session identifier
            ip_address: Optional IP address
            user_agent: Optional user agent string

        Returns:
            bool: True if tracking was successful
        """
        logger.info(
            f"Service: Tracking usage for content {content_id}, user: {user_id}"
        )

        # Validate content ID
        if not self._validate_content_id(content_id):
            logger.error(f"Invalid content ID format: {content_id}")
            return False

        try:
            content_uuid = uuid.UUID(content_id)
            result = self.repository.track_usage(
                content_id=content_uuid,
                user_id=user_id,
                event_type="copy",
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            logger.info(
                f"Service: Repository returned {result} for content {content_id}"
            )

            # Invalidate trending cache on successful tracking
            # This ensures fresh data for trending content
            if result:
                self.invalidate_trending_cache()

            return result
        except ValueError:
            logger.error(f"Invalid content ID format: {content_id}")
            return False

    def get_content_usage(self, content_id: str) -> int:
        """
        Get the usage count for a specific content item.

        Args:
            content_id: String UUID of the content item

        Returns:
            int: Usage count
        """
        if not self._validate_content_id(content_id):
            logger.error(f"Invalid content ID format: {content_id}")
            return 0

        try:
            content_uuid = uuid.UUID(content_id)
            return self.repository.get_usage_count(content_uuid)
        except Exception as e:
            logger.error(f"Error getting usage count for {content_id}: {e}")
            return 0

    def get_content_usage_stats(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed usage statistics for a content item.

        Args:
            content_id: String UUID of the content item

        Returns:
            Dict with usage statistics or None if error
        """
        if not self._validate_content_id(content_id):
            logger.error(f"Invalid content ID format: {content_id}")
            return None

        try:
            content_uuid = uuid.UUID(content_id)
            return self.repository.get_content_stats(content_uuid)
        except Exception as e:
            logger.error(f"Error getting usage stats for {content_id}: {e}")
            return None

    def enrich_content_with_usage(
        self, content_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich a list of content items with their usage statistics.

        Args:
            content_items: List of content dictionaries

        Returns:
            List of content dictionaries with added usage_count field
        """
        if not content_items:
            return content_items

        # Extract content IDs
        content_ids = []
        for item in content_items:
            try:
                if "id" in item:
                    content_ids.append(uuid.UUID(str(item["id"])))
            except (ValueError, TypeError):
                continue

        # Get usage counts in batch
        usage_counts = self.repository.get_usage_counts_batch(content_ids)

        # Add usage counts to content items
        for item in content_items:
            if "id" in item:
                item["usage_count"] = usage_counts.get(str(item["id"]), 0)
            else:
                item["usage_count"] = 0

        return content_items

    async def get_user_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for a user's contributed content.

        Args:
            user_id: User identifier

        Returns:
            Dict containing user statistics
        """
        return await self.repository.get_user_statistics(user_id)

    def get_trending_content(
        self, limit: int = 10, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get currently trending content based on recent usage.
        Uses caching to reduce database load.

        Args:
            limit: Maximum number of items to return
            hours: Time window for trending calculation (default 24 hours)

        Returns:
            List of trending content with usage stats
        """
        # Create cache key based on parameters
        cache_key = f"trending:{limit}:{hours}"

        # Try to get from cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Returning cached trending content for {cache_key}")
            return cached_result

        # Fetch from database if not in cache
        logger.debug(f"Fetching trending content from database for {cache_key}")
        trending_content = self.repository.get_trending_content(
            limit=limit, hours=hours
        )

        # Cache the result with appropriate TTL
        # Shorter TTL for smaller time windows
        ttl = 300 if hours <= 24 else 600  # 5 or 10 minutes
        self.cache.set(cache_key, trending_content, ttl_seconds=ttl)

        return trending_content

    def invalidate_trending_cache(self):
        """
        Invalidate all trending content cache entries.
        Should be called when significant usage changes occur.
        """
        count = self.cache.invalidate_pattern("trending:")
        logger.info(f"Invalidated {count} trending cache entries")

    def initialize_content_usage(self, content_id: str, initial_count: int = 0):
        """
        Initialize usage tracking for a content item.
        Used during seeding.

        Args:
            content_id: String UUID of the content item
            initial_count: Initial usage count
        """
        if not self._validate_content_id(content_id):
            logger.error(f"Invalid content ID format: {content_id}")
            return

        try:
            content_uuid = uuid.UUID(content_id)
            self.repository.initialize_usage_data(content_uuid, initial_count)
        except Exception as e:
            logger.error(f"Error initializing usage for {content_id}: {e}")

    def batch_track_usage(
        self,
        content_ids: List[str],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> bool:
        """
        Track usage for multiple content items at once.

        Args:
            content_ids: List of content ID strings
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            bool: True if all tracking was successful
        """
        valid_ids = []
        for content_id in content_ids:
            if self._validate_content_id(content_id):
                valid_ids.append(uuid.UUID(content_id))
            else:
                logger.warning(f"Skipping invalid content ID in batch: {content_id}")

        if not valid_ids:
            logger.error("No valid content IDs in batch")
            return False

        try:
            return self.repository.batch_track_usage(
                content_ids=valid_ids,
                user_id=user_id,
                event_type="copy",
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"Error in batch tracking: {e}")
            return False

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Clean up old usage events from the database.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            int: Number of records deleted
        """
        logger.info(f"Cleaning up usage events older than {days_to_keep} days")
        try:
            deleted_count = self.repository.cleanup_old_events(days_to_keep)
            logger.info(f"Deleted {deleted_count} old usage event records")
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0

    def get_usage_count(self, content_id: str) -> int:
        """
        Get only the usage count for a content item (lightweight).

        Args:
            content_id: String UUID of the content item

        Returns:
            int: Usage count
        """
        return self.get_content_usage(content_id)


# Global service instance
_usage_service: Optional[UsageTrackingService] = None


def get_usage_service() -> UsageTrackingService:
    """Get or create the global usage tracking service instance."""
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageTrackingService()
    return _usage_service

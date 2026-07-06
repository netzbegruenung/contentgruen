"""
Service layer for search tracking functionality.
Provides business logic for tracking and analyzing search behavior.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from repositories.search_tracking_repository import get_search_tracking_repository

logger = logging.getLogger(__name__)


class SearchTrackingService:
    """Service for managing search tracking."""

    def __init__(self):
        self.repository = get_search_tracking_repository()

    def track_search(
        self,
        query_text: str,
        results_count: int,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_hash: Optional[str] = None,
    ) -> bool:
        """
        Track a search event.

        Args:
            query_text: The search query text
            results_count: Number of results returned
            session_id: Optional session identifier
            user_id: Optional user identifier
            ip_hash: Optional hashed IP address

        Returns:
            bool: True if tracking was successful
        """
        # Validate inputs
        if not query_text:
            logger.warning("Cannot track search with empty query text")
            return False

        if results_count < 0:
            logger.warning(f"Invalid results_count: {results_count}")
            return False

        # Sanitize query text (truncate if too long)
        query_text = query_text[:1000] if len(query_text) > 1000 else query_text

        logger.info(
            f"Tracking search: query='{query_text[:50]}...', results={results_count}, user={user_id or 'anonymous'}"
        )

        return self.repository.track_search(
            query_text=query_text,
            results_count=results_count,
            session_id=session_id,
            user_id=user_id,
            ip_hash=ip_hash,
        )

    def get_daily_active_users(self, date: datetime) -> int:
        """
        Get count of unique active users for a specific day.

        Args:
            date: The date to check

        Returns:
            int: Count of unique users/sessions
        """
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        return self.repository.get_unique_active_users(start_of_day, end_of_day)

    def get_searches_per_user_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get search statistics per user/session.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with average, median, and distribution stats
        """
        return self.repository.get_searches_per_user(days)


# Global service instance
_search_tracking_service: Optional[SearchTrackingService] = None


def get_search_tracking_service() -> SearchTrackingService:
    """Get or create the global search tracking service instance."""
    global _search_tracking_service
    if _search_tracking_service is None:
        _search_tracking_service = SearchTrackingService()
    return _search_tracking_service

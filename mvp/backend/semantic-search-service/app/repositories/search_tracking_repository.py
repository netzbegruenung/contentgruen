"""
Repository for search event tracking.
Handles database operations for search analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import func, distinct, and_, or_
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import SearchEvent

logger = logging.getLogger(__name__)


class SearchTrackingRepository:
    """Repository for managing search event data."""

    def __init__(self):
        self.db = get_app_database()

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
        try:
            with self.db.get_session() as session:
                search_event = SearchEvent(
                    query_text=query_text,
                    results_count=results_count,
                    session_id=session_id,
                    user_id=user_id,
                    ip_hash=ip_hash,
                )
                session.add(search_event)
                session.commit()
                logger.debug(
                    f"Tracked search: '{query_text[:50]}...' for user/session: {user_id or session_id}"
                )
                return True
        except Exception as e:
            logger.error(f"Error tracking search event: {e}", exc_info=True)
            return False

    def get_unique_active_users(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> int:
        """
        Get count of unique active users (both authenticated and anonymous sessions).

        Args:
            start_date: Start of period
            end_date: End of period (defaults to now)

        Returns:
            int: Count of unique users/sessions
        """
        if end_date is None:
            end_date = datetime.utcnow()

        try:
            with self.db.get_session() as session:
                # Count distinct authenticated users
                user_count = (
                    session.query(func.count(distinct(SearchEvent.user_id)))
                    .filter(
                        and_(
                            SearchEvent.timestamp >= start_date,
                            SearchEvent.timestamp <= end_date,
                            SearchEvent.user_id.isnot(None),
                            SearchEvent.user_id != "anonymous",
                        )
                    )
                    .scalar()
                    or 0
                )

                # Count distinct anonymous sessions
                session_count = (
                    session.query(func.count(distinct(SearchEvent.session_id)))
                    .filter(
                        and_(
                            SearchEvent.timestamp >= start_date,
                            SearchEvent.timestamp <= end_date,
                            SearchEvent.session_id.isnot(None),
                            or_(
                                SearchEvent.user_id.is_(None),
                                SearchEvent.user_id == "anonymous",
                            ),
                        )
                    )
                    .scalar()
                    or 0
                )

                total = user_count + session_count
                logger.debug(
                    f"Active users {start_date} to {end_date}: {user_count} users + {session_count} sessions = {total}"
                )
                return total
        except Exception as e:
            logger.error(f"Error getting unique active users: {e}", exc_info=True)
            return 0

    def get_searches_per_user(self, days: int = 7) -> Dict[str, Any]:
        """
        Get search statistics per user/session.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with average, median, and distribution stats
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            with self.db.get_session() as session:
                # Get search counts per user
                user_searches = (
                    session.query(
                        SearchEvent.user_id,
                        func.count(SearchEvent.id).label("search_count"),
                    )
                    .filter(
                        and_(
                            SearchEvent.timestamp >= start_date,
                            SearchEvent.user_id.isnot(None),
                            SearchEvent.user_id != "anonymous",
                        )
                    )
                    .group_by(SearchEvent.user_id)
                    .all()
                )

                # Get search counts per session (anonymous)
                session_searches = (
                    session.query(
                        SearchEvent.session_id,
                        func.count(SearchEvent.id).label("search_count"),
                    )
                    .filter(
                        and_(
                            SearchEvent.timestamp >= start_date,
                            SearchEvent.session_id.isnot(None),
                            or_(
                                SearchEvent.user_id.is_(None),
                                SearchEvent.user_id == "anonymous",
                            ),
                        )
                    )
                    .group_by(SearchEvent.session_id)
                    .all()
                )

                # Combine counts
                all_counts = [count for _, count in user_searches] + [
                    count for _, count in session_searches
                ]

                if not all_counts:
                    return {
                        "average": 0.0,
                        "median": 0,
                        "total_users": 0,
                        "total_searches": 0,
                    }

                all_counts.sort()
                total_users = len(all_counts)
                total_searches = sum(all_counts)
                average = total_searches / total_users if total_users > 0 else 0
                median = all_counts[len(all_counts) // 2] if all_counts else 0

                return {
                    "average": round(average, 2),
                    "median": median,
                    "total_users": total_users,
                    "total_searches": total_searches,
                }
        except Exception as e:
            logger.error(f"Error getting searches per user: {e}", exc_info=True)
            return {"average": 0.0, "median": 0, "total_users": 0, "total_searches": 0}

    def get_search_count_by_period(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> int:
        """
        Get total search count for a period.

        Args:
            start_date: Start of period
            end_date: End of period (defaults to now)

        Returns:
            int: Total search count
        """
        if end_date is None:
            end_date = datetime.utcnow()

        try:
            with self.db.get_session() as session:
                count = (
                    session.query(func.count(SearchEvent.id))
                    .filter(
                        and_(
                            SearchEvent.timestamp >= start_date,
                            SearchEvent.timestamp <= end_date,
                        )
                    )
                    .scalar()
                    or 0
                )
                return count
        except Exception as e:
            logger.error(f"Error getting search count: {e}", exc_info=True)
            return 0

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Clean up old search events.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            int: Number of records deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            with self.db.get_session() as session:
                deleted_count = (
                    session.query(SearchEvent)
                    .filter(SearchEvent.timestamp < cutoff_date)
                    .delete()
                )
                session.commit()
                logger.info(f"Cleaned up {deleted_count} old search events")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old search events: {e}", exc_info=True)
            return 0


# Global repository instance
_search_tracking_repository: Optional[SearchTrackingRepository] = None


def get_search_tracking_repository() -> SearchTrackingRepository:
    """Get or create the global search tracking repository instance."""
    global _search_tracking_repository
    if _search_tracking_repository is None:
        _search_tracking_repository = SearchTrackingRepository()
    return _search_tracking_repository

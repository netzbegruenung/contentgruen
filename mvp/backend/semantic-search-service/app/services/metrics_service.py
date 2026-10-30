"""
Metrics service for aggregating and analyzing application metrics.
Provides the statistics behind the admin dashboard; the Bilanz is in
services/bilanz_service.py.
"""

import logging
from datetime import datetime, timedelta, date, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import text, func, distinct, and_, or_

from repositories.search_tracking_repository import get_search_tracking_repository
from repositories.usage_tracking_repository import get_usage_repository
from infrastructure.database.connection import get_app_database

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for managing application metrics and analytics."""

    def __init__(self):
        self.search_repo = get_search_tracking_repository()
        self.usage_repo = get_usage_repository()
        self.db = get_app_database()

    def get_daily_active_users(self, target_date: Optional[date] = None) -> int:
        """
        Get count of unique active users for a specific day.
        Combines authenticated users and anonymous sessions.

        Args:
            target_date: The date to check (defaults to today)

        Returns:
            int: Count of unique users/sessions
        """
        if target_date is None:
            target_date = date.today()

        target_datetime = datetime.combine(target_date, datetime.min.time())
        return self.search_repo.get_unique_active_users(
            target_datetime,
            target_datetime.replace(hour=23, minute=59, second=59, microsecond=999999),
        )

    def get_weekly_active_users(self, start_date: Optional[date] = None) -> int:
        """
        Get count of unique active users for a week.

        Returns active user-days rather than distinct people: the search pseudonym
        rotates daily so that activity cannot be linked across days.

        Args:
            start_date: Start of the week (defaults to 7 days ago)

        Returns:
            int: Count of active user-days
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=7)

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.utcnow()

        return self.search_repo.get_unique_active_users(start_datetime, end_datetime)

    def get_searches_per_user(self, days: int = 7) -> Dict[str, Any]:
        """
        Get search statistics per user/session.

        Averaged over active user-days, see SearchesPerUserResponse.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with average, median, and distribution stats
        """
        return self.search_repo.get_searches_per_user(days)

    def get_content_created_per_week(self, weeks: int = 4) -> List[Dict[str, Any]]:
        """
        Get content creation statistics by week.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            List of dicts with week start date and content count
        """
        try:
            results = []
            end_date = datetime.utcnow()

            for week_offset in range(weeks):
                week_end = end_date - timedelta(weeks=week_offset)
                week_start = week_end - timedelta(days=7)

                # Count content created from Qdrant (approximation via usage tracking)
                # This counts unique content items that were first used in this period
                with self.db.get_session() as session:
                    count = (
                        session.execute(
                            text(
                                """
                        SELECT COUNT(*)
                        FROM usage_tracking
                        WHERE first_used >= :start_date
                        AND first_used < :end_date
                        """
                            ),
                            {"start_date": week_start, "end_date": week_end},
                        ).scalar()
                        or 0
                    )

                results.append(
                    {
                        "week_start": week_start.date().isoformat(),
                        "week_end": week_end.date().isoformat(),
                        "content_created": count,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Error getting content created per week: {e}", exc_info=True)
            return []

    def get_usage_counter_trend(self, weeks: int = 4) -> List[Dict[str, Any]]:
        """
        Get usage counter trend by week.

        Counts usage events in each 7-day window. Until #467 this summed the total
        counters of the content last used in the window, which is no weekly figure.
        Calendar weeks for the Bilanz: services/bilanz_service.py.

        Args:
            weeks: Number of weeks to analyze

        Returns:
            List of dicts with week and usage count, the latest window first
        """
        try:
            results = []
            end_date = datetime.now(timezone.utc)

            for week_offset in range(weeks):
                week_end = end_date - timedelta(weeks=week_offset)
                week_start = week_end - timedelta(days=7)

                with self.db.get_session() as session:
                    count = (
                        session.execute(
                            text(
                                """
                        SELECT COUNT(*)
                        FROM usage_events
                        WHERE timestamp >= :start_date
                        AND timestamp < :end_date
                        """
                            ),
                            {"start_date": week_start, "end_date": week_end},
                        ).scalar()
                        or 0
                    )

                results.append(
                    {
                        "week_start": week_start.date().isoformat(),
                        "week_end": week_end.date().isoformat(),
                        "usage_count": count,
                    }
                )

            return results
        except Exception as e:
            logger.error(f"Error getting usage counter trend: {e}", exc_info=True)
            return []

    def get_helpful_rate(self, days: int = 7) -> Dict[str, Any]:
        """
        Get the "War hilfreich" rate (percentage of likes vs total votes).

        Args:
            days: Number of days to analyze

        Returns:
            Dict with like_count, dislike_count, total, and percentage
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            with self.db.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT
                        COUNT(CASE WHEN vote_type = 'like' THEN 1 END) as like_count,
                        COUNT(CASE WHEN vote_type = 'dislike' THEN 1 END) as dislike_count,
                        COUNT(*) as total_votes
                    FROM votes
                    WHERE created >= :start_date
                    """
                    ),
                    {"start_date": start_date},
                ).fetchone()

                if result and result[2] > 0:  # total_votes > 0
                    like_count = result[0] or 0
                    dislike_count = result[1] or 0
                    total_votes = result[2] or 0
                    helpful_rate = (
                        (like_count / total_votes * 100) if total_votes > 0 else 0
                    )

                    return {
                        "like_count": like_count,
                        "dislike_count": dislike_count,
                        "total_votes": total_votes,
                        "helpful_rate": round(helpful_rate, 2),
                    }
                else:
                    return {
                        "like_count": 0,
                        "dislike_count": 0,
                        "total_votes": 0,
                        "helpful_rate": 0.0,
                    }
        except Exception as e:
            logger.error(f"Error getting helpful rate: {e}", exc_info=True)
            return {
                "like_count": 0,
                "dislike_count": 0,
                "total_votes": 0,
                "helpful_rate": 0.0,
            }

    def get_mvp_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Get all MVP metrics in one comprehensive call, without goals.

        Returns:
            Dict with all key metrics for the dashboard
        """
        try:
            # Get current metrics
            dau = self.get_daily_active_users()
            searches_stats = self.get_searches_per_user(days=7)
            content_created = self.get_content_created_per_week(weeks=1)
            usage_trend = self.get_usage_counter_trend(weeks=2)
            helpful_stats = self.get_helpful_rate(days=7)

            # Calculate usage trend direction
            trend_direction = "stable"
            current_week_usage = 0
            previous_week_usage = 0
            if len(usage_trend) >= 2:
                current_week_usage = usage_trend[0]["usage_count"]
                previous_week_usage = usage_trend[1]["usage_count"]
                if current_week_usage > previous_week_usage * 1.1:  # 10% increase
                    trend_direction = "increasing"
                elif current_week_usage < previous_week_usage * 0.9:  # 10% decrease
                    trend_direction = "decreasing"
            elif len(usage_trend) == 1:
                current_week_usage = usage_trend[0]["usage_count"]

            # Get total usage counter sum
            with self.db.get_session() as session:
                usage_counter_total = (
                    session.execute(
                        text("SELECT COALESCE(SUM(usage_count), 0) FROM usage_tracking")
                    ).scalar()
                    or 0
                )

            # Bewusst ohne Zielwerte (#417): Die Bilanz vergleicht mit der Basislinie
            # aus dem internen Launch, nicht mit festen Zahlen.
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "period_days": 7,
                "daily_active_users": dau,
                "searches_per_user": searches_stats.get("average", 0),
                "content_created_this_week": (
                    content_created[0]["content_created"] if content_created else 0
                ),
                "usage_counter_total": usage_counter_total,
                "usage_counter_current_week": current_week_usage,
                "usage_counter_previous_week": previous_week_usage,
                "usage_counter_trend": trend_direction,
                "helpful_rate": helpful_stats.get("helpful_rate", 0),
                "helpful_like_count": helpful_stats.get("like_count", 0),
                "helpful_dislike_count": helpful_stats.get("dislike_count", 0),
                "helpful_total_votes": helpful_stats.get("total_votes", 0),
            }
        except Exception as e:
            logger.error(f"Error getting MVP dashboard metrics: {e}", exc_info=True)
            raise

    def get_content_creation_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed content creation statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with creation statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            with self.db.get_session() as session:
                total_content = (
                    session.execute(
                        text(
                            """
                    SELECT COUNT(*)
                    FROM usage_tracking
                    WHERE first_used >= :start_date
                    """
                        ),
                        {"start_date": start_date},
                    ).scalar()
                    or 0
                )

                return {
                    "period_days": days,
                    "total_content_created": total_content,
                    "average_per_day": (
                        round(total_content / days, 2) if days > 0 else 0
                    ),
                }
        except Exception as e:
            logger.error(f"Error getting content creation stats: {e}", exc_info=True)
            return {
                "period_days": days,
                "total_content_created": 0,
                "average_per_day": 0,
            }


# Global service instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get or create the global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service

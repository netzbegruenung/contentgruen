"""
Service layer for search tracking functionality.
Provides business logic for tracking and analyzing search behavior.

No personally identifiable data is persisted. Callers hand in the user or session
id, this layer turns it into a daily rotating pseudonym, and only that pseudonym
reaches the database.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.config import settings
from repositories.search_tracking_repository import get_search_tracking_repository

logger = logging.getLogger(__name__)

# Fallback secret when actor_hash_secret is not configured. Random per process, so
# pseudonyms are never reproducible from the stored data alone -- at the cost of a
# fresh pseudonym space after every restart.
_FALLBACK_SECRET = secrets.token_hex(32)


class SearchTrackingService:
    """Service for managing search tracking."""

    def __init__(self):
        self.repository = get_search_tracking_repository()

    @staticmethod
    def _derive_actor_hash(
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        moment: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Derive the daily pseudonym for a searching actor.

        The pseudonym is HMAC-SHA256 over "<actor id>|<UTC date>" keyed with the
        configured secret. Two properties matter:

        - It cannot be reversed to a user or session id without the secret, so the
          stored value is not personally identifiable.
        - The UTC date is part of the message, so the same person gets a different
          pseudonym every day and search activity cannot be linked across days.

        Args:
            user_id: Identifier of the authenticated user, if any
            session_id: Anonymous session identifier, if any
            moment: Point in time the pseudonym belongs to (defaults to now, UTC)

        Returns:
            64-character hex digest, or None if there is no actor to identify
        """
        actor_id = user_id or session_id
        if not actor_id:
            return None

        if moment is None:
            moment = datetime.now(timezone.utc)
        day = moment.strftime("%Y-%m-%d")

        secret = settings.actor_hash_secret or _FALLBACK_SECRET
        return hmac.new(
            secret.encode("utf-8"),
            f"{actor_id}|{day}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def track_search(
        self,
        results_count: int,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Track a search event.

        The search text itself is deliberately not accepted here -- it used to be
        stored in full and was never read back by any query.

        Args:
            results_count: Number of results returned
            session_id: Optional session identifier, hashed before storage
            user_id: Optional user identifier, hashed before storage

        Returns:
            bool: True if tracking was successful
        """
        if results_count < 0:
            logger.warning(f"Invalid results_count: {results_count}")
            return False

        actor_hash = self._derive_actor_hash(user_id=user_id, session_id=session_id)

        logger.info(f"Tracking search: results={results_count}")

        return self.repository.track_search(
            results_count=results_count,
            actor_hash=actor_hash,
        )

    def get_daily_active_users(self, date: datetime) -> int:
        """
        Get count of unique active users for a specific day.

        Exact: the pseudonym rotates daily, so within a single day one actor maps
        to exactly one pseudonym.

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

        Counted per active user-day, not per person: an actor searching on three
        days of the window counts three times, because the pseudonyms rotate daily.

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

"""
Service layer for usage tracking functionality.
Provides business logic for tracking and retrieving usage statistics.
"""

import logging
from typing import Optional, List, Dict, Any
import uuid
import hashlib

from domain.content_registry import BEITRAGSTYPEN_WERTE
from domain.models.commentary import Fassung
from domain.models.content_type import ContentType
from repositories.gesehene_nutzung_repository import (
    GeseheneNutzungRepository,
    get_gesehene_nutzung_repository,
)
from repositories.usage_tracking_repository import get_usage_repository
from services.cache.cache_manager import get_trending_cache

logger = logging.getLogger(__name__)


class UsageTrackingService:
    """Service for managing usage tracking."""

    def __init__(self, gesehene_nutzung: Optional[GeseheneNutzungRepository] = None):
        self.repository = get_usage_repository()
        self.cache = get_trending_cache()
        # Erst beim ersten Besuch geholt: die globale Instanz baut eine Verbindung auf.
        self._gesehene_nutzung = gesehene_nutzung

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
        session_id: Optional[str] = None,
        device_category: Optional[str] = None,
        fassung: Optional[str] = None,
    ) -> bool:
        """
        Track that a content item was used (copied).

        Args:
            content_id: String UUID of the content item
            session_id: Optional session identifier
            device_category: Grobe Geraetekategorie, bereits abgeleitet
            fassung: Die kopierte Fassung eines Kommentars (#355), sonst None

        Returns:
            bool: True if tracking was successful
        """
        logger.info(f"Service: Tracking usage for content {content_id}")

        # Validate content ID
        if not self._validate_content_id(content_id):
            logger.error(f"Invalid content ID format: {content_id}")
            return False

        try:
            content_uuid = uuid.UUID(content_id)
            result = self.repository.track_usage(
                content_id=content_uuid,
                event_type="copy",
                session_id=session_id,
                device_category=device_category,
                fassung=fassung,
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

    def nutzung_letzte_7_tage_nachtragen(
        self, content_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Traegt ``nutzung_letzte_7_tage`` nach: wie oft jeder Inhalt in den letzten
        7 Tagen genutzt wurde, fuer "Meine Beitraege" (#349).
        """
        content_ids = []
        for item in content_items:
            try:
                content_ids.append(uuid.UUID(str(item["id"])))
            except (KeyError, ValueError, TypeError):
                continue
        zuwachs = self.repository.get_nutzung_letzte_7_tage_batch(content_ids)
        for item in content_items:
            item["nutzung_letzte_7_tage"] = zuwachs.get(str(item.get("id")), 0)
        return content_items

    def nutzung_je_fassung_nachtragen(
        self, content_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Traegt ``nutzung_je_fassung`` nach: am Kommentar je vorhandener Fassung die
        Nutzung und ihr Zuwachs der letzten 7 Tage (#355), fuer "Meine Beitraege".
        Andere Beitragstypen haben keine Fassungen und bekommen None.

        Mittel hat jeder Kommentar, Kurz und Lang nur, wenn sie Text haben. Die
        Reihenfolge ist Kurz, Mittel, Lang wie die Reiter der Karte. Nutzung ohne
        Fassung (von vor #355) steht hier nicht; sie steckt nur in ``usage_count``.
        """

        def hat_text(wert: Any) -> bool:
            return isinstance(wert, str) and bool(wert.strip())

        def fassungen(item: Dict[str, Any]) -> List[str]:
            vorhanden = [
                (Fassung.KURZ, hat_text(item.get("short_text"))),
                (Fassung.MITTEL, True),
                (Fassung.LANG, hat_text(item.get("long_text"))),
            ]
            return [fassung.value for fassung, da in vorhanden if da]

        kommentare = {}
        for item in content_items:
            item["nutzung_je_fassung"] = None
            if item.get("content_type") != ContentType.COMMENTARY:
                continue
            try:
                kommentare[uuid.UUID(str(item["id"]))] = item
            except (KeyError, ValueError, TypeError):
                continue
        je_fassung = self.repository.get_nutzung_je_fassung_batch(list(kommentare))
        for content_id, item in kommentare.items():
            gezaehlt = je_fassung.get(str(content_id), {})
            item["nutzung_je_fassung"] = {
                fassung: gezaehlt.get(fassung, {"nutzung": 0, "letzte_7_tage": 0})
                for fassung in fassungen(item)
            }
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

    async def nutzung_seit_letztem_besuch(self, user_id: str) -> int:
        """
        Wie oft die Beitraege der Person seit ihrem letzten Besuch genutzt wurden,
        fuer die Rueckmeldung beim Anmelden (#349). Der Aufruf zaehlt als Besuch: Danach
        gilt die heutige Nutzung als gesehen.

        Verglichen wird die Gesamtnutzung der Beitraege wie in "Meine Beitraege":
        ohne Aussagen und Herkunftsangaben, die keine Beitraege sind, und ohne eigene
        Kopien, die gar nicht erst gezaehlt werden.
        """
        stats = await self.repository.get_user_statistics(
            user_id, content_types=BEITRAGSTYPEN_WERTE
        )
        if self._gesehene_nutzung is None:
            self._gesehene_nutzung = get_gesehene_nutzung_repository()
        return self._gesehene_nutzung.neu_seit_letztem_besuch(
            user_id, nutzung_jetzt=stats["total_usage_count"]
        )

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
